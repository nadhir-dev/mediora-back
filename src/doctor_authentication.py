from typing import List, TYPE_CHECKING
from src.utils.time import now
from datetime import datetime
from uuid import UUID
from src.db import BASE
from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .users import Users


class DoctorRequest(BASE):

    __tablename__ = "doctor_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    reviewed: Mapped[bool] = mapped_column(default=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    wallet_password: Mapped[str] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    user: Mapped["Users"] = relationship(back_populates="requests")
    request_media: Mapped[List["RequestMedia"]] = relationship(
        back_populates="doctor_request"
    )


class Media(BASE):
    __tablename__ = "media"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column()
    public_id: Mapped[str] = mapped_column()
    resource_type: Mapped[str] = mapped_column()
    format: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now)

    # request_media: Mapped["RequestMedia"] = relationship(back_populates="media")
    __table_args__ = (
        # UniqueConstraint(
        #     "public_id",
        #     "resource_type",
        #     name="unique_public_id_per_resource_type",
        # ),
    )


class RequestMedia(BASE):

    __tablename__ = "request_media"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column()

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_requests.id"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("media.id", ondelete="cascade")
    )
    media: Mapped["Media"] = relationship(uselist=False)
    doctor_request: Mapped["DoctorRequest"] = relationship()
