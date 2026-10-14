"""HTTP routes: staff actions (spec: staff-approval) and read-only observability (spec:
observability-api).

No sign-in yet: the staff member's name is taken from the request body. Authentication
belongs to the deployment work, before this API is reachable by anyone else.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.approvals import NotWaiting, decide, review_queue
from app.db import get_sessionmaker
from app.enums import ApprovalAction
from app.observability import (
    RESULTS_DIR,
    eval_reports,
    is_resting,
    list_requests,
    metrics,
    request_detail,
    snapshot,
)
from app.orchestrator import process_request
from app.transitions import TransitionConflict

router = APIRouter()

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ReplyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Sessions = Annotated[async_sessionmaker[AsyncSession], Depends(get_sessionmaker)]


def get_results_dir() -> Path:
    return RESULTS_DIR


ResultsDir = Annotated[Path, Depends(get_results_dir)]


@dataclass(frozen=True)
class StreamTiming:
    poll_seconds: float = 0.5
    limit_seconds: float = 300.0


def get_stream_timing() -> StreamTiming:
    return StreamTiming()


Timing = Annotated[StreamTiming, Depends(get_stream_timing)]


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApproveBody(_Body):
    staff_name: Name


class EditAndApproveBody(_Body):
    staff_name: Name
    reply: ReplyText


class RejectBody(_Body):
    staff_name: Name
    reason: Reason


@router.get("/requests")
async def requests(
    sessions: Sessions, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[dict[str, Any]]:
    async with sessions() as session:
        return await list_requests(session, limit)


@router.get("/requests/{request_id}")
async def request(request_id: uuid.UUID, sessions: Sessions) -> dict[str, Any]:
    async with sessions() as session:
        try:
            return await request_detail(session, request_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="booking request not found") from exc


@router.get("/requests/{request_id}/events")
async def events(request_id: uuid.UUID, sessions: Sessions, timing: Timing) -> StreamingResponse:
    """Server-sent events: a snapshot now and whenever the state or a span changes, until
    the request is resting with nothing running (decision record 0013).

    The run may be happening in another process (the command line), so the stream reads
    the database, which every process writes to, rather than listening in memory.
    """
    async with sessions() as session:
        try:
            await snapshot(session, request_id)  # 404 before the stream starts
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="booking request not found") from exc

    async def stream() -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timing.limit_seconds
        last = None
        while True:
            async with sessions() as session:
                snap = await snapshot(session, request_id)
            data = json.dumps(snap, sort_keys=True)
            if data != last:
                yield f"event: snapshot\ndata: {data}\n\n"
                last = data
            if is_resting(snap) or loop.time() >= deadline:
                break
            await asyncio.sleep(timing.poll_seconds)
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/metrics")
async def get_metrics(sessions: Sessions) -> dict[str, Any]:
    async with sessions() as session:
        return await metrics(session)


@router.get("/evals")
async def evals(results_dir: ResultsDir) -> list[dict[str, Any]]:
    return eval_reports(results_dir)


@router.get("/reviews")
async def reviews(sessions: Sessions) -> list[dict[str, Any]]:
    async with sessions() as session:
        return await review_queue(session)


@router.post("/requests/{request_id}/approve")
async def approve(request_id: uuid.UUID, body: ApproveBody, sessions: Sessions) -> dict[str, str]:
    return await _act(sessions, request_id, ApprovalAction.APPROVE, body.staff_name)


@router.post("/requests/{request_id}/edit-and-approve")
async def edit_and_approve(
    request_id: uuid.UUID, body: EditAndApproveBody, sessions: Sessions
) -> dict[str, str]:
    return await _act(
        sessions, request_id, ApprovalAction.EDIT_AND_APPROVE, body.staff_name, reply=body.reply
    )


@router.post("/requests/{request_id}/reject")
async def reject(request_id: uuid.UUID, body: RejectBody, sessions: Sessions) -> dict[str, str]:
    return await _act(
        sessions, request_id, ApprovalAction.REJECT, body.staff_name, reason=body.reason
    )


async def _act(
    sessions: async_sessionmaker[AsyncSession],
    request_id: uuid.UUID,
    action: ApprovalAction,
    staff_name: str,
    **details: str,
) -> dict[str, str]:
    try:
        await decide(sessions, request_id, action, staff_name, **details)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="booking request not found") from exc
    except (NotWaiting, TransitionConflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # The decision is committed; resume the run from the new state (send, no model call).
    status = await process_request(request_id, sessions=sessions)
    return {"status": str(status)}
