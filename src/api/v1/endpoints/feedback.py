from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db.connection import get_db
from src.models.users import Users
from src.schemas.feedback import (
    FeedBackWithoutPatientResponse,
    FeedBacksResponse,
)
from src.services.authentication import protect
from src.services.feedback import (
    add_feedback,
    delete_feedback,
    get_feedback,
    update_feedback,
)

feedback_router = APIRouter(prefix="")


@feedback_router.get("/{doctor_id}/feedback", response_model=FeedBacksResponse)
async def get_patients_feedback(
    session: Annotated[AsyncSession, Depends(get_db)], doctor_id: UUID
):
    feedback = await get_feedback(db=session, doctor_id=doctor_id)

    return {"data": feedback}


@feedback_router.post(
    "/{doctor_id}/feedback", response_model=FeedBackWithoutPatientResponse
)
async def feedback(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Users, Depends(protect)],
    doctor_id: UUID,
    body: Annotated[str, Body(embed=True)],
):
    feedback = await add_feedback(db=session, user=user, doctor_id=doctor_id, body=body)

    return {"data": feedback}


@feedback_router.delete("/feedback/{feedback_id}")
async def remove_feedback(
    session: Annotated[AsyncSession, Depends(get_db)],
    feedback_id: UUID,
    user: Annotated[Users, Depends(protect)],
    response: Response,
):
    await delete_feedback(db=session, user=user, feedback_id=feedback_id)
    response.status_code = status.HTTP_204_NO_CONTENT


@feedback_router.patch(
    "/feedback/{feedback_id}", response_model=FeedBackWithoutPatientResponse
)
async def edit_feedback(
    session: Annotated[AsyncSession, Depends(get_db)],
    feedback_id: UUID,
    user: Annotated[Users, Depends(protect)],
    body: Annotated[str, Body(embed=True)],
):
    feedback = await update_feedback(
        db=session, user=user, feedback_id=feedback_id, body=body
    )

    return {"data": feedback}
