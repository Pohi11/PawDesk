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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.approvals import NotWaiting, decide, review_queue
from app.certificate_card import render as render_certificate
from app.db import get_sessionmaker
from app.demo import (
    DEMO_TODAY,
    SAMPLES,
    sample_certificate,
    sample_pets,
    store_request,
    submit_sample,
)
from app.demo_generator import MAX_SEED, fresh_seed, generate
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


def get_llm_kwargs() -> dict[str, Any]:
    """Extra model-client arguments for background runs; tests inject a scripted model."""
    return {}


LLMKwargs = Annotated[dict[str, Any], Depends(get_llm_kwargs)]
MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
PetName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


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


class DemoBody(_Body):
    """A fixed sample by id, or a generated request by its seed (exactly one)."""

    sample: str | None = None
    seed: int | None = None
    message: MessageText | None = None

    @model_validator(mode="after")
    def _one_source(self):
        if (self.sample is None) == (self.seed is None):
            raise ValueError("send either a sample or a seed")
        if self.seed is not None and not 0 <= self.seed <= MAX_SEED:
            raise ValueError(f"seed must be between 0 and {MAX_SEED}")
        return self


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


@router.get("/demo/samples")
async def demo_samples(sessions: Sessions) -> list[dict[str, Any]]:
    """The fixed samples, each with its pet's photo fields (null when not on file)."""
    async with sessions() as session:
        pets = await sample_pets(session)
    return [
        sample.to_json()
        | {
            "pet": pet.name if (pet := pets[sample.id]) else sample.pet,
            "pet_id": str(pet.id) if pet else None,
            "pet_species": str(pet.species) if pet else None,
            "pet_breed": pet.breed if pet else None,
        }
        for sample in SAMPLES.values()
    ]


@router.get("/demo/samples/{sample_id}/certificate.png")
async def demo_sample_certificate(sample_id: str) -> Response:
    image = sample_certificate(sample_id)
    if image is None:
        raise HTTPException(status_code=404, detail="this sample has no certificate")
    return Response(content=image, media_type="image/png")


@router.get("/demo/generate")
async def demo_generate(
    sessions: Sessions,
    seed: Annotated[int | None, Query(ge=0, le=MAX_SEED)] = None,
    avoid: Annotated[list[PetName], Query(max_length=20)] = [],  # noqa: B006 (FastAPI copies it)
) -> dict[str, Any]:
    """A random request with a matching certificate. Nothing is stored: the seed alone
    reproduces it for the preview image and for sending. Without a seed, the server picks
    one whose pet name is on no pet on file and none of `avoid` (recent names)."""
    async with sessions() as session:
        if seed is None:
            seed = await fresh_seed(session, avoid)
        request = await generate(session, seed)
    return request.to_json() | {
        "certificate_url": f"/demo/generated/{request.seed}/certificate.png"
    }


@router.get("/demo/generated/{seed}/certificate.png")
async def demo_generated_certificate(seed: int, sessions: Sessions) -> Response:
    if not 0 <= seed <= MAX_SEED:
        raise HTTPException(status_code=404, detail="no such generated request")
    async with sessions() as session:
        request = await generate(session, seed)
    return Response(content=render_certificate(request), media_type="image/png")


@router.post("/demo/requests", status_code=202)
async def demo_request(
    body: DemoBody, sessions: Sessions, background: BackgroundTasks, llm_kwargs: LLMKwargs
) -> dict[str, str]:
    """Store the sample as a new request and answer at once; processing runs afterward."""
    try:
        if body.seed is not None:
            async with sessions() as session:
                generated = await generate(session, body.seed)
            request_id = await store_request(
                sessions,
                generated.owner_email,
                body.message or generated.message,
                render_certificate(generated),
                generated.new_pet(),
            )
        else:
            request_id = await submit_sample(sessions, body.sample, body.message)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background.add_task(
        process_request, request_id, sessions=sessions, today=DEMO_TODAY, **llm_kwargs
    )
    return {"id": str(request_id)}


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
