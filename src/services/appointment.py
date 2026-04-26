from datetime import date
from datetime import date as d
import hashlib
import hmac
import json
from uuid import UUID

from fastapi import HTTPException, Request
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, update
from sqlalchemy.orm import joinedload, selectinload
from starlette import status

from src.config.env import env
from src.models.Appointments import (
    AppointmentPaymentSession,
    AppointmentPayments,
    Appointments,
    DoctorServices,
    Payments,
)
from src.models.messaging import ConversationMembers, Conversations
from src.models.users import Users
from src.schemas.appointment import AppointmentStatus, MakeAppointment
from src.schemas.doctor_schedule import IsDoctorFree
from src.schemas.users import User
from src.services.doctor_schedule import check_if_doctor_is_free
from src.utils.authentication import gen_id, gen_token
from src.utils.time import after, now


async def create_appointment_session(
    *,
    db: AsyncSession,
    user: User,
    appointment_info: MakeAppointment,
):

    stmt = select(AppointmentPaymentSession.checkout_url).where(
        AppointmentPaymentSession.service_id == appointment_info.service_id,
        AppointmentPaymentSession.patient_id == user.id,
        AppointmentPaymentSession.is_expired == False,
        AppointmentPaymentSession.expires_at > now(),
    )

    existing_session_url = (await db.scalars(stmt)).one_or_none()

    if existing_session_url:
        return existing_session_url

    await check_if_doctor_is_free(
        db=db,
        info=IsDoctorFree(
            service_id=appointment_info.service_id, date=appointment_info.date
        ),
    )

    service = await db.get(DoctorServices, appointment_info.service_id)

    if service.doctor_id == user.id:  # type:ignore
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "you cannot make an appointment with yourself."
        )

    async with httpx.AsyncClient() as client:

        success_url = f"{env.url}/appointments/chargily-webhook"

        response = await client.post(
            url=env.chargily_checkout_endpoint,
            headers={
                "Authorization": f"Bearer {env.chargily_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "amount": service.price,  # type:ignore
                "currency": "dzd",
                "success_url": success_url,
            },
        )

        data = response.json()

    session = AppointmentPaymentSession(
        service_id=appointment_info.service_id,
        patient_id=user.id,
        date=appointment_info.date,
        expires_at=after(minutes=30),
        checkout_url=data["checkout_url"],  # type:ignore
    )
    db.add(session)

    await db.commit()
    return data["checkout_url"]  # type:ignore


async def handle_chargilypay_webhook(
    *,
    db: AsyncSession,
    request: Request,
):

    signature = request.headers.get("signature")

    if not signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    body = await request.body()

    computed_signature = hmac.new(
        env.chargily_secret_key.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, computed_signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    try:
        event = json.loads(body)
    except json.JSONDecodeError:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON"
        )

    event_type = event.get("type")
    data = event.get("data")

    if event_type == "checkout.paid":
        stmt = select(AppointmentPaymentSession).where(
            AppointmentPaymentSession.checkout_url == data["checkout_url"]
        )

        session = (await db.scalars(stmt)).one()

        doctor_id = await db.scalar(
            select(DoctorServices.doctor_id).where(
                DoctorServices.id == session.service_id
            )
        )

        if session.is_expired:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "already processed.")

        appointment = Appointments(
            id=gen_id(),
            service_id=session.service_id,
            doctor_id=doctor_id,
            patient_id=session.patient_id,
            date=session.date,
            token=gen_token(),
        )

        payment = Payments(
            id=gen_id(),
            reciever_id=appointment.doctor_id,
            sender_id=appointment.patient_id,
            ammount=data.get("amount", 0),
            payment_session=session.id,
        )

        appointment_payment = AppointmentPayments(
            payment_id=payment.id, type="service payment"
        )

        session.is_expired = True
        conversation = Conversations(id=gen_id(), name="for later", is_group=False)

        user_membership = ConversationMembers(
            user_id=session.patient_id, conversation_id=conversation.id
        )
        doctor_membership = ConversationMembers(
            user_id=doctor_id, conversation_id=conversation.id
        )

        db.add_all(
            [
                appointment,
                payment,
                appointment_payment,
                conversation,
                user_membership,
                doctor_membership,
            ]
        )
        await db.commit()

    elif event_type == "checkout.failed":

        stmt = (
            update(AppointmentPaymentSession)
            .where(AppointmentPaymentSession.checkout_url == data.url)
            .values(expired=True)
        )
        await db.execute(stmt)
        await db.commit()


async def fetch_patient_appointments(
    db: AsyncSession,
    user: User,
    status: AppointmentStatus,
    date: date | None,
    page: int,
    limit: int,
):
    condition = (Appointments.patient_id == user.id) & (Appointments.status == status)

    if date:
        condition = condition & (Appointments.date == date)
    else:
        condition = condition & (Appointments.date >= d.today())

    stmt = (
        select(Appointments)
        .where(condition)
        .options(
            selectinload(Appointments.doctor).load_only(
                Users.first_name,
                Users.last_name,
                Users.username,
                Users.is_doctor,
                Users.specialty,
                Users.joined_at,
                Users.picture,
            )
        )
        .order_by(Appointments.created_at)
        .limit(limit)
        .offset((page - 1) * limit)
    )

    return (await db.scalars(stmt)).all()


async def fetch_doctor_appointments(
    db: AsyncSession,
    user: User,
    appointmentStatus: AppointmentStatus,
    date: date,
    page: int,
    limit: int,
):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "only allowed doctors are allowed."
        )

    stmt = (
        select(Appointments)
        .where(
            Appointments.doctor_id == user.id,
            Appointments.status == appointmentStatus,
            Appointments.date == date,
        )
        .options(
            selectinload(Appointments.patient).load_only(
                Users.first_name,
                Users.last_name,
                Users.is_doctor,
                Users.username,
                Users.specialty,
                Users.joined_at,
                Users.picture,
            )
        )
        .order_by(
            Appointments.created_at,
        )
        .limit(limit)
        .offset((page - 1) * limit)
    )

    return (await db.scalars(stmt)).all()


async def fetch_appointment(*, db: AsyncSession, user: User, appointment_id: UUID):

    stmt = (
        select(Appointments)
        .where(
            Appointments.id == appointment_id,
            or_(
                Appointments.doctor_id == user.id,
                Appointments.patient_id == user.id,
            ),
        )
        .options(
            joinedload(Appointments.patient).load_only(
                Users.first_name,
                Users.last_name,
                Users.is_doctor,
                Users.username,
                Users.specialty,
                Users.joined_at,
                Users.picture,
            ),
            joinedload(Appointments.doctor).load_only(
                Users.first_name,
                Users.last_name,
                Users.is_doctor,
                Users.username,
                Users.specialty,
                Users.joined_at,
                Users.picture,
            ),
            joinedload(Appointments.service).load_only(
                DoctorServices.price,
                DoctorServices.name,
                DoctorServices.description,
                DoctorServices.created_at,
            ),
        )
    )

    data = (await db.scalars(stmt)).one_or_none()

    if not data:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    return data


async def settle_appointment(*, db: AsyncSession, user: User, appointment_id: UUID):
    stmt = select(Appointments).where(
        Appointments.id == appointment_id,
        Appointments.patient_id == user.id,
    )

    appointment = (await db.scalars(stmt)).one_or_none()

    if not appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    if appointment.status != AppointmentStatus.scheduled.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"this appointment is already {appointment.status}.",
        )

    appointment.status = AppointmentStatus.completed.value

    await db.commit()


async def cancel_appointment_out(*, db: AsyncSession, user: User, appointment_id: UUID):
    stmt = select(Appointments).where(
        Appointments.id == appointment_id,
        Appointments.patient_id == user.id,
    )

    appointment = (await db.scalars(stmt)).one_or_none()

    if not appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    if appointment.status != AppointmentStatus.scheduled.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"this appointment is already {appointment.status}.",
        )

    appointment.status = AppointmentStatus.cancelled.value

    await db.commit()


async def check_appointment_token(*, db: AsyncSession, user: User, token: str):

    stmt = select(Appointments).where(Appointments.token == token)

    appointment = (await db.scalars(stmt)).one_or_none()

    if not appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "there is no appointments matching this token."
        )

    if appointment.doctor_id != user.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "this appointment is with another doctor."
        )
    return appointment
