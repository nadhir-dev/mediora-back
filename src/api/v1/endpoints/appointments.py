from datetime import date
from typing import Annotated
from uuid import UUID
from fastapi.responses import RedirectResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends, Header, Query, Response

from src.db.connection import get_db
from src.schemas.appointment import AppointmentStatus, MakeAppointment
from src.schemas.users import User

from src.services.appointment import (
    cancel_appointment_out,
    create_appointment_session,
    fetch_appointment,
    fetch_doctor_appointments,
    fetch_patient_appointments,
    handle_chargilypay_webhook,
    settle_appointment,
)
from src.services.authentication import protect


appointments_router = APIRouter(prefix="/appointments")


# @appointments_router.post("/")
# async def make_appointment(
#    session: Annotated[AsyncSession, Depends(get_db)],
#     user: Annotated[User, Depends(protect)],
# ):
#     pass


@appointments_router.get("/")
async def get_appointments(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    status: AppointmentStatus = AppointmentStatus.scheduled,
    date: date = date.today(),
):
    output = await fetch_patient_appointments(
        db=session, user=user, status=status, date=date
    )
    return {"data": output}


@appointments_router.get("/patients")
async def get_doctor_appointments(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    status: AppointmentStatus = AppointmentStatus.scheduled,
    date: date = date.today(),
):
    output = await fetch_doctor_appointments(
        db=session, user=user, appointmentStatus=status, date=date
    )
    return {"data": output}


@appointments_router.post("/")
async def make_appointment(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    data: Annotated[MakeAppointment, Body()],
):
    url = await create_appointment_session(db=session, user=user, appointment_info=data)

    return {"data": {"url": url}}


@appointments_router.post("/chargily-webhook", include_in_schema=False)
async def chargily_webhook_success(
    session: Annotated[AsyncSession, Depends(get_db)],
    # user: Annotated[User, Depends(protect)],
    request: Request,
):

    await handle_chargilypay_webhook(db=session, request=request)

    return {"message": "success"}


@appointments_router.get("/chargily-webhook", include_in_schema=False)
async def chargily_webhoo_success(
    session: Annotated[AsyncSession, Depends(get_db)],
    # user: Annotated[User, Depends(protect)],
    request: Request,
):

    await handle_chargilypay_webhook(db=session, request=request)

    return {"message": "success"}


@appointments_router.get("/{appointment_id}")
async def get_appointment(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
):
    output = await fetch_appointment(
        db=session, user=user, appointment_id=appointment_id
    )

    return {"data": output}


@appointments_router.post("/{appointment_id}/approve")
async def approve_appointment_settlement(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
):
    output = await settle_appointment(
        db=session, user=user, appointment_id=appointment_id
    )

    return {"data": output}


@appointments_router.delete("/{appointment_id}/cancel")
async def cancel_appointment(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
):
    output = await cancel_appointment_out(
        db=session, user=user, appointment_id=appointment_id
    )

    return {"data": output}
