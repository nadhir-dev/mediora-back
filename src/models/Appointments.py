from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import date
from sqlalchemy import ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.connection import BASE
from src.schemas.appointment import AppointmentStatus
from src.utils.time import now

if TYPE_CHECKING:
    from .users import Users


class Appointments(BASE):
    __tablename__ = "appointments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_services.id", ondelete="cascade")
    )
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    date: Mapped["date"] = mapped_column()
    token: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column(default=AppointmentStatus.scheduled.value)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)

    doctor: Mapped["Users"] = relationship("Users", foreign_keys=[doctor_id])
    patient: Mapped["Users"] = relationship("Users", foreign_keys=[patient_id])


class Payments(BASE):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reciever_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="cascade")
    )
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)
    ammount: Mapped[int] = mapped_column()
    payment_session: Mapped[UUID] = mapped_column(
        ForeignKey("appointment_payment_sessions.id", ondelete="cascade")
    )

    reciever: Mapped["Users"] = relationship("Users", foreign_keys=[reciever_id])
    sender: Mapped["Users"] = relationship("Users", foreign_keys=[sender_id])


class AppointmentPayments(BASE):
    __tablename__ = "appointment_payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="cascade")
    )
    type: Mapped[str] = mapped_column()
    notes: Mapped[str] = mapped_column(nullable=True)

    payment: Mapped["Payments"] = relationship("Payments", foreign_keys=[payment_id])


class AppointmentPaymentSession(BASE):
    __tablename__ = "appointment_payment_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    service_id: Mapped[UUID] = mapped_column(ForeignKey("doctor_services.id"))
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    date: Mapped["date"] = mapped_column()
    checkout_url: Mapped[str] = mapped_column()
    is_expired: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(True))

    patient: Mapped["Users"] = relationship("Users", foreign_keys=[patient_id])
    # patient: Mapped["Users"] = relationship(
    #     "Users", back_populates="patient_appointments", foreign_keys=[patient_id]
    # )


class DoctorWallet(BASE):
    __tablename__ = "doctor_wallet"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    balance: Mapped[int] = mapped_column(default=0)
    doctor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    password: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)

    user: Mapped["Users"] = relationship("Users", foreign_keys=[doctor_id])


class PayOffs(BASE):
    __tablename__ = "payoffs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    balance: Mapped[int] = mapped_column()
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)


class DoctorServices(BASE):
    __tablename__ = "doctor_services"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    price: Mapped[int] = mapped_column()
    chargily_pay_price_id: Mapped[str] = mapped_column()
    chargily_pay_product_id: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)

    user: Mapped["Users"] = relationship("Users", foreign_keys=[doctor_id])

    __table_args__ = (
        UniqueConstraint("name", "doctor_id", name="unique_service_name_per_user"),
    )
