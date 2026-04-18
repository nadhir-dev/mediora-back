from datetime import time, date, timedelta, datetime
from datetime import date as d
from typing import List, Optional, Self, override
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette import status

from src.config.env import env

class WorkingDayWithoutDayOfWeek(BaseModel):
    starting_time: time = Field()
    finish_time: time = Field()
    max_appointments: int = Field(gt=0, le=20)

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.starting_time >= self.finish_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "working time is contradictory, (starting time >= finish time)",
            )

        start = datetime.combine(date.today(), self.starting_time)
        end = datetime.combine(date.today(), self.finish_time)

        if end - start < timedelta(hours=1):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "working time is too short, at least one hour.",
            )
        # if self.day_of_week > 6 or self.day_of_week < 0:
        #     raise HTTPException(
        #         status.HTTP_400_BAD_REQUEST,
        #         "working day is contradictory, (6 >= working day >= 0)",
        #     )

        return self

    model_config = ConfigDict(from_attributes=True)

class WorkingDay(WorkingDayWithoutDayOfWeek):
    day_of_week: int = Field(ge=0, le=6)

    model_config = ConfigDict(from_attributes=True)


# class WorkingDayExtended(WorkingDay):
#     id: UUID
#     user_id: UUID
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)


class WorkingDayExtended(BaseModel):
    id: UUID
    user_id: UUID
    day_of_week: int
    starting_time: time
    finish_time: time
    max_appointments: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkingDaysResponse(BaseModel):
    data: list[WorkingDayExtended]

    model_config = ConfigDict(from_attributes=True)


class WorkingDaysRange(BaseModel):

    start: int = Field(ge=0, le=6)
    end: int = Field(ge=0, le=6)
    schedule: WorkingDayWithoutDayOfWeek

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.end < self.start:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "working time is contradictory, (start > end)",
            )
        # if self.start < 0 or self.end > 6:
        #     raise HTTPException(
        #        status.HTTP_400_BAD_REQUEST,
        #         "working day is contradictory, (6 >= working day >= 0)",
        #     )

        return self




class WorkingDays(BaseModel):
    schedule: WorkingDaysRange | List[WorkingDay]

 


class RestTime(BaseModel):
    starting_time: time
    finish_time: time
    day_of_week: int = Field(ge=0, le=6)
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.starting_time >= self.finish_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "working time is contradictory, (starting time >= finish time)",
            )

        start = datetime.combine(date.today(), self.starting_time)
        end = datetime.combine(date.today(), self.finish_time)

        if end - start < timedelta(minutes=5):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "rest is too short, at least five minutes long.",
            )
        return self


class RestTimeExtended(BaseModel):
    id: UUID
    user_id: UUID
    starting_time: time
    finish_time: time
    day_of_week: int
    reason: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# class RestTimeExtended(RestTime):
#     id: UUID
#     user_id: UUID
#     created_at: datetime
#     model_config = ConfigDict(from_attributes=True)


class RestTimeResponse(BaseModel):
    data: RestTimeExtended

    model_config = ConfigDict(from_attributes=True)


class RestTimeRange(BaseModel):
    rest: RestTime
    start: int = Field(ge=0, le=6)
    end: int = Field(ge=0, le=6)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end < self.start:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "time is contradictory, (start > end)",
            )
        return self


class RestTimes(BaseModel):
    schedule: List[RestTime] | RestTimeRange

    @model_validator(mode="before")
    def fix(cls, data):
        if not isinstance(data.get("schedule"), list):
            data.get("schedule")["day_of_week"] = 0
        return data


class SpecialSchedule(BaseModel):
    starting_time: Optional[time] = None
    finish_time: Optional[time] = None
    date: date
    is_vacation: bool | None = None
    max_appointments: int = Field(gt=0)
    # reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if not self.is_vacation and (not self.finish_time or not self.starting_time):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "must provide either is_vacation or starting_time and finish_time.",
            )

        if self.starting_time and self.finish_time:

            start = datetime.combine(date.today(), self.starting_time)
            end = datetime.combine(date.today(), self.finish_time)

            if end - start < timedelta(hours=1):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "working time is too short, at least one hour.",
                )
        # if self.max_appointments and self.max_appointments <= 0:
        #     raise HTTPException(
        #         status.HTTP_400_BAD_REQUEST,
        #         "limit must be > 0",
        #     )
        if date.today() >= self.date:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "the date is contradictory (the date provided is already gone).",
            )

        return self


class SpecialScheduleExtended(BaseModel):
    id: UUID
    user_id: UUID
    starting_time: Optional[time] = None
    finish_time: Optional[time] = None
    date: date
    is_vacation: Optional[bool] = None
    max_appointments: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# class SpecialScheduleExtended(SpecialSchedule):
#     id: UUID
#     user_id: UUID
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)


class SpecialScheduleResponse(BaseModel):
    data: list[SpecialScheduleExtended]
    model_config = ConfigDict(from_attributes=True)


class SpecialScheduleRange(BaseModel):
    schedule: SpecialSchedule
    start: int = Field(ge=0, le=6)
    end: int = Field(ge=0, le=6)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end < self.start:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "working time is contradictory, (start > end)",
            )
        return self


class SpecialSchedules(BaseModel):
    schedule: List[SpecialSchedule] | SpecialScheduleRange


class Leave(BaseModel):
    starting_date: date
    finish_date: Optional[date] = None
    period_in_days: Optional[int] = Field(None, gt=0)
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if not self.finish_date and not self.period_in_days:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "you have to provide either of these fields finish_date or period_in_days.",
            )
        if date.today() + timedelta(days=7) > self.starting_date:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "leaves have to be scheduled a at least a week ealier.",
            )

        if (
            self.finish_date is not None
            and self.starting_date + timedelta(days=1) > self.finish_date
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "leaves have to be at least one day long.",
            )

        return self


class LeaveExtended(BaseModel):
    id: UUID
    user_id: UUID
    starting_date: date
    finish_date: date
    reason: Optional[str] = None
    created_at: datetime


class LeaveResponse(BaseModel):
    data: LeaveExtended


class TimeOff(BaseModel):
    starting_time: time
    finish_time: Optional[time] = None
    duration_in_minutes: Optional[int] = Field(None, gt=0)
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if not self.finish_time and not self.duration_in_minutes:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "you have to provide either of these fields finish_time or duration_in_minutes.",
            )

        if self.finish_time is not None:
            start = datetime.combine(date.today(), self.starting_time)
            end = datetime.combine(date.today(), self.finish_time)

            if start >= end + timedelta(minutes=5):

                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "timeoff has to be 5 minutes long at least.",
                )
        return self


class TimeOffExtended(BaseModel):
    starting_time: time
    finish_time: Optional[time] = None
    reason: Optional[str] = None
    date: date
    id: UUID
    user_id: UUID
    created_at: datetime


class TimeOffResponse(BaseModel):
    data: TimeOffExtended


class TimeOffsfResponse(BaseModel):
    data: list[TimeOffExtended]


class SpecialRestTime(BaseModel):
    starting_time: time
    finish_time: time
    date: "date"
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.starting_time >= self.finish_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "time is contradictory, (starting time >= finish time)",
            )

        start = datetime.combine(date.today(), self.starting_time)
        end = datetime.combine(date.today(), self.finish_time)

        if end - start < timedelta(minutes=5):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "rest is too short, at least five minutes long.",
            )
        return self


class SpecialRestTimeExtended(SpecialRestTime):
    id: UUID
    user_id: UUID
    created_at: datetime


class SpecialRestTimeResponse(BaseModel):
    data: SpecialRestTimeExtended

    model_config = ConfigDict(from_attributes=True)


class SpecialRestTimeRange(BaseModel):
    rest: SpecialRestTime
    start: int = Field(ge=0, le=6)
    end: int = Field(ge=0, le=6)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end < self.start:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "time is contradictory, (start > end)",
            )
        return self


class SpecialRestTimes(BaseModel):
    schedule: List[SpecialRestTime] | SpecialRestTimeRange

    @model_validator(mode="before")
    def fix(cls, data):
        if not isinstance(data.get("schedule"), list):
            data.get("schedule")["day_of_week"] = 0
        return data


class IsDoctorFree(BaseModel):
    service_id: UUID
    date: date

    @field_validator("date")
    @classmethod
    def field(cls, v):
        date_after_week = date.today() + timedelta(days=7)

        if v >= date_after_week:
            raise ValueError("you cannot make appointments after 7 days from now.")

        if v <= date.today():
            raise ValueError("you cannot make appointments for today or earlier.")

        return v


class FetchWorkingDays(BaseModel):
    day_of_week: int


class FetchSpecialSchedule(BaseModel):

    include_rest_times: bool = True
    date: d | None = None


class WorkingDayWithRestTimes(WorkingDayExtended):
    rest_times: list[RestTimeExtended]

    model_config = ConfigDict(from_attributes=True)


class SpecialScheduleWithRestTimes(SpecialScheduleExtended):
    rest_times: list[SpecialRestTimes]

    model_config = ConfigDict(from_attributes=True)


class WorkingDayWithRestTimesResponse(BaseModel):
    data: list[WorkingDayWithRestTimes]

    model_config = ConfigDict(from_attributes=True)


class SpecialScheduleWithRestTimesResponse(BaseModel):
    data: list[SpecialScheduleWithRestTimes | SpecialScheduleExtended]

    model_config = ConfigDict(from_attributes=True)


class DoctorService(BaseModel):
    name: str = Field(min_length=1)
    price: int = Field(ge=0, le=env.maximum_service_price, examples=[1000])
    description: str = Field(min_length=1)


class DoctorServiceExtended(BaseModel):
    id: UUID
    doctor_id: UUID

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    created_at: datetime


class DoctorServiceResponse(BaseModel):
    data: DoctorServiceExtended
class DoctorServicesResponse(BaseModel):
    data: list[DoctorServiceExtended]
