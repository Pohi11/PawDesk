"""HTTP routes for staff (spec: staff-approval).

No sign-in yet: the staff member's name is taken from the request body. Authentication
belongs to the deployment work, before this API is reachable by anyone else.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.approvals import NotWaiting, decide, review_queue
from app.db import get_sessionmaker
from app.enums import ApprovalAction
from app.orchestrator import process_request
from app.transitions import TransitionConflict

router = APIRouter()

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ReplyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Sessions = Annotated[async_sessionmaker[AsyncSession], Depends(get_sessionmaker)]


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
