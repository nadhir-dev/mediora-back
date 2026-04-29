from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from src.models.Appointments import Appointments, DoctorServices
from src.models.feedback import FeedBack
from src.models.users import Users


async def add_feedback(*, db: AsyncSession, user: Users, doctor_id: UUID, body: str):
    subquery = select(DoctorServices.id).where(DoctorServices.doctor_id == doctor_id)

    stmt = select(
        exists().where(
            Appointments.patient_id == user.id, Appointments.service_id.in_(subquery)
        )
    )

    already_had_appointment = await db.scalar(stmt)

    if not already_had_appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "you didn't have any prior appointments together with this doctor.",
        )
    feedback = FeedBack(body=body, patient_id=user.id, doctor_id=doctor_id)

    db.add(feedback)
    await db.commit()
    return feedback


async def get_feedback(*, db: AsyncSession, doctor_id: UUID):
    stmt = select(
        exists(Users).where(
            Users.is_doctor.is_(True), Users.is_active.is_(True), Users.id == doctor_id
        )
    )
    doctor_exists = await db.scalar(stmt)
    if not doctor_exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no users matching this id.")

    stmt = (
        select(FeedBack)
        .where(FeedBack.doctor_id == doctor_id)
        .options(joinedload(FeedBack.patient))
    )

    feedback = (await db.scalars(stmt)).all()

    return feedback


async def delete_feedback(*, db: AsyncSession, user: Users, feedback_id: UUID):

    stmt = (
        delete(FeedBack)
        .where(FeedBack.id == feedback_id, FeedBack.patient_id == user.id)
        .returning(FeedBack.id)
    )
    result = await db.scalar(stmt)

    if not result:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "this id matches no feedback of yours."
        )
    await db.commit()


async def update_feedback(
    *, db: AsyncSession, user: Users, feedback_id: UUID, body: str
):

    stmt = (
        update(FeedBack)
        .where(FeedBack.id == feedback_id, FeedBack.patient_id == user.id)
        .values(body=body)
        .returning(FeedBack)
    )

    feedback = (await db.scalars(stmt)).one_or_none()

    if not feedback:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "this id matches no feedback of yours."
        )

    await db.commit()

    return feedback
