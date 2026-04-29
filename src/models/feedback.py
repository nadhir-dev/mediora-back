from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from src.db.connection import BASE
from src.utils.authentication import gen_id
from src.utils.time import now

if TYPE_CHECKING:
    from src.models.users import Users


class FeedBack(BASE):
    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_id)
    body: Mapped[str] = mapped_column()
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(True), default=now, onupdate=now
    )

    doctor: Mapped["Users"] = relationship("Users", foreign_keys=[doctor_id])
    patient: Mapped["Users"] = relationship("Users", foreign_keys=[patient_id])
