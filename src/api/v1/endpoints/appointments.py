from datetime import date
from typing import Annotated
from uuid import UUID
from fastapi import Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends, Response
from starlette import status

from src.db.connection import get_db
from src.schemas.appointment import (
    AppointmentResponse,
    AppointmentStatus,
    CheckoutUrlResponse,
    DoctorAppointmentsResponse,
    ExtendedAppointmentResponse,
    MakeAppointment,
    PatientAppointmentsResponse,
)
from src.schemas.users import SuccessMessage, User

from src.services.appointment import (
    cancel_appointment_out,
    check_appointment_token,
    create_appointment_session,
    fetch_appointment,
    fetch_doctor_appointments,
    fetch_patient_appointments,
    handle_chargilypay_webhook,
    settle_appointment,
)
from src.services.authentication import protect


appointments_router = APIRouter(prefix="/appointments")


@appointments_router.get("/", response_model=PatientAppointmentsResponse)
async def get_appointments(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    status: AppointmentStatus = AppointmentStatus.scheduled,
    date: date | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
):
    output = await fetch_patient_appointments(
        db=session,
        user=user,
        status=status,
        date=date,
        limit=limit,
        page=page,
    )
    return {"data": output}


@appointments_router.get("/patients", response_model=DoctorAppointmentsResponse)
async def get_doctor_appointments(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    status: AppointmentStatus = AppointmentStatus.scheduled,
    date: date = date.today(),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
):
    output = await fetch_doctor_appointments(
        db=session,
        user=user,
        appointmentStatus=status,
        date=date,
        limit=limit,
        page=page,
    )
    return {"data": output}


@appointments_router.post("/", response_model=CheckoutUrlResponse)
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
    request: Request,
):

    await handle_chargilypay_webhook(db=session, request=request)

    return {"message": "success"}


@appointments_router.get(
    "/{appointment_id}", response_model=ExtendedAppointmentResponse
)
async def get_appointment(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
):
    output = await fetch_appointment(
        db=session, user=user, appointment_id=appointment_id
    )

    return {"data": output}


@appointments_router.post("/{appointment_id}/approve", response_model=SuccessMessage)
async def approve_appointment_settlement(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
):
    await settle_appointment(db=session, user=user, appointment_id=appointment_id)

    return {"message": "appointment approved successfully."}


@appointments_router.delete("/{appointment_id}/cancel")
async def cancel_appointment(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    appointment_id: UUID,
    response: Response,
):
    await cancel_appointment_out(db=session, user=user, appointment_id=appointment_id)

    response.status_code = status.HTTP_204_NO_CONTENT


@appointments_router.get("/check/{token}", response_model=AppointmentResponse)
async def check_appointment_status(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    token: Annotated[str, Path(min_length=4)],
):

    appointment = await check_appointment_token(db=session, user=user, token=token)

    return {"data": appointment}
