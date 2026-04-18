from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.connection import get_db
from src.schemas.doctor_schedule import (
    DoctorService,
    DoctorServiceResponse,
    DoctorServicesResponse,
    FetchSpecialSchedule,
    IsDoctorFree,
    Leave,
    LeaveResponse,
    LeavesResponse,
    RestTime,
    RestTimeResponse,
    SpecialRestTime,
    SpecialRestTimeResponse,
    SpecialScheduleResponse,
    SpecialScheduleWithRestTimesResponse,
    TimeOff,
    TimeOffResponse,
    TimeOffsfResponse,
    WorkingDayWithRestTimesResponse,
    WorkingDaysResponse,
    WorkingDays,
    RestTime,
    SpecialSchedules,
)
from src.schemas.users import DoctorListResponse, Speciality, SuccessMessage, User
from src.services.authentication import protect
from src.services.doctor_schedule import (
    add_service,
    check_if_doctor_is_free,
    delete_leave,
    delete_special_schedule,
    delete_timeoff,
    delete_working_day,
    fetch_leaves,
    fetch_special_schedules,
    fetch_timeoffs,
    get_doctor_services,
    get_some_doctors,
    get_working_times,
    modify_rest_hours,
    modify_working_time,
    schedule_leave,
    schedule_timeoff,
    add_special_schedule,
    modify_special_rest_times,
)


schedule_router = APIRouter(prefix="/doctors")


@schedule_router.get("/", response_model=DoctorListResponse)
async def fetch_doctors(
    session: Annotated[AsyncSession, Depends(get_db)],
    speciality: Speciality | None = None,
    limit: int = Query(10, ge=1),
    page: int = Query(1, ge=1),
):
    doctors = await get_some_doctors(
        db=session, limit=limit, page=page, specialty=speciality
    )

    return {"data": doctors}


@schedule_router.post("/schedule", response_model=WorkingDaysResponse)
async def add_or_change_working_hours(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    schedule: WorkingDays,
):
    working_day = await modify_working_time(db=session, user=user, schedule=schedule)

    return {"data": working_day}


@schedule_router.post("/schedule/rest", response_model=RestTimeResponse)
async def add_or_change_rest_hours(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    rest_time_info: RestTime,
):
    rest_time = await modify_rest_hours(db=session, user=user, rest_time=rest_time_info)

    return {"data": rest_time}


@schedule_router.post("/timeoffs", response_model=TimeOffResponse)
async def add_timeoff(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    timeoff_info: TimeOff,
):
    timeoff = await schedule_timeoff(db=session, user=user, timeoff_info=timeoff_info)

    return {"data": timeoff}


@schedule_router.post("/special-schedules", response_model=SpecialScheduleResponse)
async def add_or_change_special_schedule(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    special_schedule_info: SpecialSchedules,
):
    special_schedule = await add_special_schedule(
        db=session, user=user, special_schedule=special_schedule_info
    )

    return {"data": special_schedule}


@schedule_router.post("/special-schedules/rest", response_model=SpecialRestTimeResponse)
async def add_or_change_special_rest_hours(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    rest_time_info: SpecialRestTime,
):
    rest_time = await modify_special_rest_times(
        db=session, user=user, rest_time=rest_time_info
    )

    return {"data": rest_time}


@schedule_router.post("/leaves", response_model=LeaveResponse)
async def add_leave(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    leave_info: Leave,
):
    leave = await schedule_leave(db=session, user=user, leave_info=leave_info)

    return {"data": leave}


@schedule_router.get(
    "/{doctor_id}/schedule", response_model=WorkingDayWithRestTimesResponse
)
async def get_schedule(
    session: Annotated[AsyncSession, Depends(get_db)],
    doctor_id: UUID,
):
    schedule = await get_working_times(db=session, doctor_id=doctor_id)

    return {"data": schedule}


@schedule_router.get(
    "{doctor_id}/special-schedules", response_model=SpecialScheduleWithRestTimesResponse
)
async def get_special_schedules(
    # user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    doctor_id: UUID,
    date: date | None = None,
    include_rest_times: bool = True,
):
    special_schedules = await fetch_special_schedules(
        db=session,
        doctor_id=doctor_id,
        info=FetchSpecialSchedule(date=date, include_rest_times=include_rest_times),
    )

    return {"data": special_schedules}


@schedule_router.get("/leaves", response_model=LeavesResponse)
async def get_leaves(
    doctor_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    include_passed_ones: bool = False,
):
    leaves = await fetch_leaves(
        db=session, doctor_id=doctor_id, include_passed_ones=include_passed_ones
    )

    return {"data": leaves}


@schedule_router.get("/timeoffs", response_model=TimeOffsfResponse)
async def get_timeoffs(
    doctor_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    timeoffs = await fetch_timeoffs(db=session, doctor_id=doctor_id)

    return {"data": timeoffs}


@schedule_router.delete("/{id}", response_model=SuccessMessage)
async def remove_working_day(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
):
    await delete_working_day(db=session, user=user, id=id)

    return {"message": "working day removed successfully."}


@schedule_router.delete("/special-schedules/{id}", response_model=SuccessMessage)
async def remove_special_schedule(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
):
    await delete_special_schedule(
        db=session,
        user=user,
        id=id,
    )

    return {"message": "special schedule removed successfully."}


@schedule_router.delete("/leaves/{id}", response_model=SuccessMessage)
async def remove_leave(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
):
    await delete_leave(db=session, user=user, id=id)

    return {"message": "special schedule removed successfully."}


@schedule_router.delete("/timeoffs/{id}", response_model=SuccessMessage)
async def remove_timeoff(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
):
    await delete_timeoff(db=session, user=user, id=id)

    return {"message": "special schedule removed successfully."}


@schedule_router.post("/services", response_model=DoctorServiceResponse)
async def add_new_service(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    info: DoctorService,
):

    output = await add_service(db=session, user=user, service_info=info)

    return {"data": output}


@schedule_router.get("/{doctor_id}/services", response_model=DoctorServicesResponse)
async def fetch_doctor_services(
    session: Annotated[AsyncSession, Depends(get_db)],
    doctor_id: UUID,
):

    services = await get_doctor_services(db=session, doctor_id=doctor_id)

    return {"data": services}


@schedule_router.get("/is-free", response_model=SuccessMessage)
async def can_doctor_take_appointments(
    session: Annotated[AsyncSession, Depends(get_db)],
    # user: Annotated[User, Depends(protect)],
    info: Annotated[IsDoctorFree, Query()],
    # service_id: UUID,
    # date: date,
):
    await check_if_doctor_is_free(db=session, info=info)

    return {"message": "doctor is free to accept appointments."}
