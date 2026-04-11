from datetime import datetime, date
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, DateTime, Date, null
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db import BASE
from src.utils.time import now


if TYPE_CHECKING:
    from src.models.doctor_authentication import DoctorRequest, Media


class Users(BASE):

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    is_doctor: Mapped[bool] = mapped_column(default=False)
    role: Mapped[str] = mapped_column(default="user")  # user, doctor, admin
    specialty: Mapped[Optional[str]] = mapped_column(nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_active: Mapped[bool] = mapped_column(default=True)
    picture: Mapped[Optional[str]] = mapped_column(nullable=True)
    picture_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("profile_media.id", ondelete="SET NULL"), nullable=True
    )

    auth: Mapped["Auth"] = relationship(
        back_populates="user",
        uselist=False,
    )
    info: Mapped["Info"] = relationship(uselist=False)
    # sessions: Mapped[List["Sessions"]] = relationship(
    #     back_populates="user", uselist=True
    # )

    requests: Mapped["DoctorRequest"] = relationship(
        back_populates="user", uselist=False
    )


class Auth(BASE):
    __tablename__ = "auth"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), primary_key=True
    )
    google_open_id: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)

    password: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_password_reset: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now
    )
    # is_verified: Mapped[bool] = mapped_column(default=False)

    otp_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    otp_code_purpose: Mapped[Optional[str]] = mapped_column(nullable=True)
    otp_code_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    reset_token_purpose: Mapped[Optional[str]] = mapped_column(nullable=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["Users"] = relationship(back_populates="auth")
    # sessions: Mapped[List["Sessions"]] = relationship(
    #     back_populates="auth", uselist=True
    # )


class Info(BASE):
    __tablename__ = "info"

    gender: Mapped[Optional[str]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    clinic_posx: Mapped[Optional[str]] = mapped_column(nullable=True)
    clinic_posy: Mapped[Optional[str]] = mapped_column(nullable=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(nullable=True)
    degree: Mapped[Optional[str]] = mapped_column(nullable=True)
    institution: Mapped[Optional[str]] = mapped_column(nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # phone number should be unique only if we verify it
    # it is still not a concern now, cz we don't use it for sth critical
    phone: Mapped[Optional[str]] = mapped_column(nullable=True)

    id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), primary_key=True
    )


class Sessions(BASE):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    refresh_token: Mapped[str] = mapped_column(unique=True)
    refresh_token_expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[str] = mapped_column(index=True)

    invoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    # auth_id: Mapped[UUID] = mapped_column(ForeignKey("auth.id", ondelete="cascade"))

    user: Mapped["Users"] = relationship()
    # auth: Mapped["Auth"] = relationship(back_populates="sessions")


class PendingEmails(BASE):
    __tablename__ = "pending_emails"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True)
    code: Mapped[Optional[str]] = mapped_column(nullable=True)
    code_issued: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    code_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    token: Mapped[Optional[str]] = mapped_column(nullable=True)
    token_issued: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_verified: Mapped[bool] = mapped_column(default=False)


class ProfileMedia(BASE):
    __tablename__ = "profile_media"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("media.id", ondelete="cascade")
    )
    media: Mapped["Media"] = relationship(uselist=False)
