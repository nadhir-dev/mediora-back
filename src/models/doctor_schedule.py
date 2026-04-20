from uuid import UUID, uuid4
from typing import TYPE_CHECKING, List, Optional
from datetime import time, datetime, date
from sqlalchemy import (
    ForeignKey,
    SMALLINT,
    CheckConstraint,
    TIMESTAMP,
    ForeignKeyConstraint,
    Index,
    Time,
    Date,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from src.db import BASE
from src.utils.time import now

if TYPE_CHECKING:
    from src.models.users import Users


class WorkingDays(BASE):
    __tablename__ = "working_days"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(type_=SMALLINT)
    starting_time: Mapped[time] = mapped_column(Time(timezone=False))
    max_appointments: Mapped[int] = mapped_column()
    finish_time: Mapped[time] = mapped_column(Time(timezone=False))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=now, onupdate=now
    )

    user: Mapped["Users"] = relationship()
    rest_times: Mapped[List["RestTimes"]] = relationship(back_populates="working_days")

    __table_args__ = (
        CheckConstraint("finish_time > starting_time", name="finish_after_start"),
        CheckConstraint(
            "day_of_week >= 0 and day_of_week < 7", name="valid_day_of_week"
        ),
        UniqueConstraint("user_id", "day_of_week", name="unique_schedule"),
    )


class RestTimes(BASE):
    __tablename__ = "rest_times"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column()
    starting_time: Mapped[time] = mapped_column(Time(timezone=False))
    finish_time: Mapped[time] = mapped_column(Time(timezone=False))
    day_of_week: Mapped["date"] = mapped_column(type_=SMALLINT)
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now)

    working_days: Mapped["WorkingDays"] = relationship(back_populates="rest_times")

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "day_of_week"],
            ["working_days.user_id", "working_days.day_of_week"],
            ondelete="cascade",
        ),
        CheckConstraint("finish_time > starting_time", name="finish_after_start"),
    )


class SpecialSchedules(BASE):
    __tablename__ = "special_schedules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped["date"] = mapped_column(index=True)
    max_appointments: Mapped[int] = mapped_column()
    is_vacation: Mapped[bool] = mapped_column(default=False)
    starting_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=True)
    finish_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=now,
        onupdate=now,
    )

    rest_times: Mapped[List["SpecialRestTimes"]] = relationship(
        back_populates="special_schedule"
    )
    __table_args__ = (
        Index("doctor_date_index", "date", "user_id"),
        UniqueConstraint(
            "date",
            "user_id",
            name="unique_special_schedule_per_day",
        ),
        CheckConstraint(
            "finish_time > starting_time", name="ck_special_schedule_time_valid"
        ),
    )


class SpecialRestTimes(BASE):
    __tablename__ = "special_rest_times"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column()
    starting_time: Mapped[time] = mapped_column(Time(timezone=False))
    finish_time: Mapped[time] = mapped_column(Time(timezone=False))
    date: Mapped["date"] = mapped_column()
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now)

    special_schedule: Mapped["SpecialSchedules"] = relationship(
        back_populates="rest_times"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "date"],
            ["special_schedules.user_id", "special_schedules.date"],
            ondelete="cascade",
        ),
        CheckConstraint("finish_time > starting_time", name="finish_after_start"),
    )


class Leaves(BASE):
    __tablename__ = "leaves"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    starting_date: Mapped[date] = mapped_column(Date)
    finish_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=now,
    )

    __table_args__ = (
        CheckConstraint("finish_date >= starting_date", name="ck_leave_date_valid"),
    )


class TimeOffs(BASE):
    __tablename__ = "time_offs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped["date"] = mapped_column(index=True)
    starting_time: Mapped[time] = mapped_column(Time(timezone=False))
    finish_time: Mapped[time] = mapped_column(Time(timezone=False))
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=now)
