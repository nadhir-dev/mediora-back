from datetime import UTC, date
from datetime import datetime
import hashlib
import hmac
import json
from uuid import UUID

from fastapi import HTTPException, Request
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload
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
from src.schemas.appointment import AppointmentStatus, MakeAppointment
from src.schemas.doctor_schedule import DoctorService, IsDoctorFree
from src.schemas.users import User
from src.services.doctor_schedule import check_if_doctor_is_free
from src.utils.authentication import gen_id, gen_token, get_token
from src.utils.time import after, now


async def create_appointment_session(
    *,
    db: AsyncSession,
    user: User,
    appointment_info: MakeAppointment,
):

    # supposing we can make further appointments today
    stmt = select(AppointmentPaymentSession).where(
        AppointmentPaymentSession.service_id == appointment_info.service_id,
        AppointmentPaymentSession.patient_id == user.id,
        AppointmentPaymentSession.is_expired == False,
        AppointmentPaymentSession.expires_at > now(),
    )

    existing_session = (await db.scalars(stmt)).one_or_none()

    if existing_session:
        # we shouldn't redirect it to this url as it may be expired
        # in the case of the patient has already paid or other cases

        existing_session.is_expired = True
        await db.commit()

    await check_if_doctor_is_free(
        db=db,
        info=IsDoctorFree(
            service_id=appointment_info.service_id, date=appointment_info.date
        ),
    )

    service = await db.get(DoctorServices, appointment_info.service_id)

    # get service amount
    async with httpx.AsyncClient() as client:

        # success_url = f"{env.protocol}://{env.url}/{env.chargily_success_endpoint}"
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
        # try:
        #     response.raise_for_status()
        # except Exception:
        #     raise HTTPException(
        #         status.HTTP_500_INTERNAL_SERVER_ERROR, "something went wrong."
        #     )
        data = response.json()

    session = AppointmentPaymentSession(
        service_id=appointment_info.service_id,
        patient_id=user.id,
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
    pass
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

    # Handle events
    event_type = event.get("type")
    data = event.get("data")

    # if event_type == "checkout.paid":

    #     stmt = select(AppointmentPaymentSession).where(
    #         AppointmentPaymentSession.checkout_url == data["url"]
    #     ).options(selectinload(AppointmentPaymentSession.patient))
    #     session = (await db.scalars(stmt)).one()
    # # id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # # service_id: Mapped[UUID] = mapped_column(
    # #     ForeignKey("doctor_services.id", ondelete="cascade")
    # # )
    # # doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    # # patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    # # date: Mapped["date"] = mapped_column()
    # # token: Mapped[str] = mapped_column()
    # # status: Mapped[str] = mapped_column(default=AppointmentStatus.scheduled.value)
    # # created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)

    #     appointment = Appointments(service_id="",doctor_id)

    #     session.is_expired = True

    #     await db.commit()

    # elif event_type == "checkout.failed":

    #     stmt = (
    #         update(AppointmentPaymentSession)
    #         .where(AppointmentPaymentSession.checkout_url == data.url)
    #         .values(expired=True)
    #     )
    #     await db.execute(stmt)
    #     await db.commit()

    #     raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

    if event_type == "checkout.paid":

        stmt = (
            select(AppointmentPaymentSession).where(
                AppointmentPaymentSession.checkout_url == data["url"]
            )
            # .options(selectinload(AppointmentPaymentSession.patient))
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
        # db.add(appointment)

        payment = Payments(
            reciever_id=appointment.doctor_id,
            sender_id=appointment.patient_id,
            ammount=data.get("amount", 0),
            payment_session=session.id,
        )
        # db.add(payment)

        session.is_expired = True
        conversation = Conversations(id=gen_id(), name="for later", is_group=False)

        user_membership = ConversationMembers(
            user_id=session.patient_id, conversation_id=conversation.id
        )
        doctor_membership = ConversationMembers(
            user_id=doctor_id, conversation_id=conversation.id
        )

        db.add_all(
            [appointment, payment, conversation, user_membership, doctor_membership]
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

    # Respond OK


# async def expire_appointment_session(
#     db: AsyncSession,
#     user: User,
#     data: MakeAppointment,
# ):
#     session = AppointmentPaymentSession(
#         service_id=data.doctor_id, patient_id=user.id, expires_at=after(minutes=30)
#     )

#     db.add(session)
#     await db.commit()


async def fetch_patient_appointments(
    db: AsyncSession,
    user: User,
    status: AppointmentStatus,
    date: date,
):

    stmt = select(Appointments).where(
        Appointments.patient_id == user.id,
        Appointments.status == status,
        Appointments.date == date,
    )

    return (await db.scalars(stmt)).all()


async def fetch_doctor_appointments(
    db: AsyncSession,
    user: User,
    appointmentStatus: AppointmentStatus,
    date: date,
):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "only allowed doctors are allowed."
        )

    stmt = select(Appointments).where(
        Appointments.doctor_id == user.id,
        Appointments.status == appointmentStatus,
        Appointments.date == date,
        #   Appointments.patient_id == user.id
    )

    return (await db.scalars(stmt)).all()


async def fetch_appointment(db: AsyncSession, user: User, appointment_id: UUID):
    # if user.is_doctor:
    #     raise HTTPException(status.HTTP_403_FORBIDDEN, "not allowed.")

    stmt = select(Appointments).where(
        Appointments.id == appointment_id,
        or_(
            Appointments.doctor_id == user.id,
            Appointments.patient_id == user.id,
        ),
        #   Appointments.patient_id == user.id
    )

    data = (await db.scalars(stmt)).one_or_none()
    if not data:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    return data


async def settle_appointment(db: AsyncSession, user: User, appointment_id: UUID):
    stmt = select(Appointments).where(
        Appointments.id == appointment_id,
        Appointments.patient_id == user.id,
    )

    appointment = (await db.scalars(stmt)).one_or_none()

    if not appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    if not appointment.status == AppointmentStatus.scheduled.value:
        raise HTTPException(400, f"this appointment is already {appointment.status}.")

    appointment.status = AppointmentStatus.completed.value

    await db.commit()
    return appointment


async def cancel_appointment_out(db: AsyncSession, user: User, appointment_id: UUID):
    stmt = select(Appointments).where(
        Appointments.id == appointment_id,
        Appointments.patient_id == user.id,
    )

    appointment = (await db.scalars(stmt)).one_or_none()

    if not appointment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no appointment matching this id."
        )

    if not appointment.status == AppointmentStatus.scheduled.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"this appointment is already {appointment.status}.",
        )

    appointment.status = AppointmentStatus.cancelled.value

    await db.commit()
    return appointment


# TODO: handle web hook with ngrok
# TODO: review the is_free endpoint
# TODO: add schemas to appointments endpoints
# TODO: update fetch doctor and patient appointments
