from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.orm import selectinload
from starlette import status

from src.config.env import env
from src.models.Appointments import Appointments
from src.models.Appointments import AppointmentPaymentSession, DoctorServices
from src.models.doctor_authentication import DoctorRequest, Media, RequestMedia
from src.models.doctor_schedule import WorkingDays
from src.models.users import Users
from src.schemas.appointment import AppointmentStatus
from src.schemas.users import Speciality, User, UserFlatResponse
from src.schemas.doctor_schedule import (
    FetchSpecialSchedule,
    IsDoctorFree,
    WorkingDays as WDSchedule,
    RestTime as RTSchema,
    Leave as LSchema,
    TimeOff as TOSchema,
    SpecialSchedules as SSSchema,
    SpecialRestTime as SRTSchema,
    DoctorService,
)
from src.models.doctor_schedule import (
    Leaves,
    RestTimes,
    SpecialRestTimes,
    SpecialSchedules,
    TimeOffs,
    WorkingDays,
)

from src.utils.helpers import (
    format_doctor_schedule,
    format_doctor_special_schedule,
)
from src.utils.time import now


async def get_doctor(*, db: AsyncSession, doctor_id: UUID):
    stmt = (
        select(Users)
        .where(
            Users.id == doctor_id, Users.is_active.is_(True), Users.is_doctor.is_(True)
        )
        .options(selectinload(Users.info))
    )

    media_stmt = (
        select(Media.url)
        .join(RequestMedia, RequestMedia.document_id == Media.id)
        .join(DoctorRequest, DoctorRequest.id == RequestMedia.id)
        .where(
            DoctorRequest.user_id == doctor_id,
            RequestMedia.document_type == "images_of_workplace",
        )
    )

    user = (await db.scalars(stmt)).one_or_none()

    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "there is no doctors matching this id."
        )
    images_of_workplace = (await db.scalars(media_stmt)).all()

    data = UserFlatResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_doctor=user.is_doctor,
        specialty=user.specialty,
        joined_at=user.joined_at,
        picture=user.picture,
        gender=user.info.gender,
        date_of_birth=user.info.date_of_birth,
        phone=user.info.phone,
        clinic_posx=user.info.clinic_posx,
        clinic_posy=user.info.clinic_posy,
        degree=user.info.degree,
        practice_start_date=user.info.practice_start_date,
        description=user.info.description,
        institution=user.info.institution,
        images_of_workplace=[media for media in images_of_workplace],
    )
    return data


async def get_some_doctors(
    *, db: AsyncSession, page: int, limit: int, specialty: Speciality | None
):
    condition = Users.is_doctor.is_(True)

    if specialty:
        condition = condition & (Users.specialty == specialty)

    doctors_stmt = (
        select(Users).where(condition).limit(limit).offset((page - 1) * limit)
    )

    doctors = (await db.scalars(doctors_stmt)).all()

    return doctors


async def modify_working_time(*, db: AsyncSession, user: User, schedule: WDSchedule):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    data = format_doctor_schedule(schedule, user.id)
    print(data)
    stmt = insert(WorkingDays).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["day_of_week", "user_id"],
        set_={
            "starting_time": stmt.excluded.starting_time,
            "finish_time": stmt.excluded.finish_time,
            "max_appointments": stmt.excluded.max_appointments,
        },
    ).returning(WorkingDays)

    output = (await db.scalars(stmt)).all()
    await db.commit()

    return output


async def delete_rest_hours(*, db: AsyncSession, user: User, rest_time_id: UUID):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    stmt = delete(RestTimes).where(RestTimes.id == rest_time_id).returning(RestTimes.id)

    output = await db.scalar(stmt)

    if output is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "there is no rest hours matching this id."
        )
    await db.commit()


async def modify_rest_hours(*, db: AsyncSession, user: User, rest_time: RTSchema):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    existence_stmt = select(
        exists().where(
            RestTimes.day_of_week == rest_time.day_of_week,
            RestTimes.user_id == user.id,
            and_(
                RestTimes.starting_time < rest_time.finish_time,
                RestTimes.finish_time > rest_time.starting_time,
            ),
        )
    )
    existence = await db.scalar(existence_stmt)

    if existence:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "there exists a rest time that overlaps with this one.",
        )

    stmt = (
        insert(RestTimes)
        .values(
            {
                "user_id": user.id,
                "starting_time": rest_time.starting_time,
                "finish_time": rest_time.finish_time,
                "day_of_week": rest_time.day_of_week,
                "reason": rest_time.reason,
            }
        )
        .returning(RestTimes)
    )

    try:
        output = (await db.scalars(stmt)).one()
        await db.commit()

    except IntegrityError as e:
        err_msg = str(e.orig).lower()

        if "rest_times_user_id_day_of_week_fkey" in err_msg:
            raise HTTPException(
                status.HTTP_409_CONFLIC,
                f"you didn't set your working hours for that day of the week.",
            )

    return output


async def delete_special_rest_hours(
    *, db: AsyncSession, user: User, rest_time_id: UUID
):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    stmt = (
        delete(SpecialRestTimes)
        .where(SpecialRestTimes.id == rest_time_id)
        .returning(SpecialRestTimes.id)
    )

    output = await db.scalar(stmt)

    if output is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "there is no special rest hours matching this id.",
        )
    await db.commit()


async def schedule_leave(*, db: AsyncSession, user: User, leave_info: LSchema):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    finish_date = (
        leave_info.finish_date
        if leave_info.finish_date is not None
        else leave_info.starting_date
        + timedelta(days=leave_info.period_in_days)  # type:ignore
    )

    reason = leave_info.reason

    existence_stmt = select(
        exists(Leaves).where(
            Leaves.user_id == user.id,
            Leaves.starting_date < finish_date,
            Leaves.finish_date > leave_info.starting_date,
        )
    )

    existing_leaves = await db.scalar(existence_stmt)

    if existing_leaves:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "you have already schedule a leave within this range.",
        )

    leave = Leaves(
        user_id=user.id,
        starting_date=leave_info.starting_date,
        finish_date=finish_date,
        reason=reason,
    )

    db.add(leave)
    await db.commit()

    return leave


async def schedule_timeoff(*, db: AsyncSession, user: User, timeoff_info: TOSchema):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    today = date.today()
    day_of_week = today.weekday()

    finish_time = (
        timeoff_info.finish_time
        if timeoff_info.finish_time is not None
        else timeoff_info.starting_time
        + timedelta(minutes=timeoff_info.duration_in_minutes)  # type:ignore
    )
    stmt = select(
        exists(WorkingDays)
        .where(
            WorkingDays.user_id == user.id,
            WorkingDays.day_of_week == day_of_week,
            WorkingDays.starting_time <= timeoff_info.starting_time,
            WorkingDays.finish_time >= finish_time,
        )
        .label("works_today"),
        exists(Leaves)
        .where(
            Leaves.user_id == user.id,
            and_(
                Leaves.starting_date <= today,
                Leaves.finish_date >= today,
            ),
        )
        .label("on_leave_schedule"),
        exists(SpecialSchedules)
        .where(SpecialSchedules.user_id == user.id, SpecialSchedules.date == today)
        .label("any_special_schedule"),
        exists(TimeOffs)
        .where(
            TimeOffs.user_id == user.id,
            TimeOffs.date == today,
            TimeOffs.starting_time < finish_time,
            TimeOffs.finish_time > timeoff_info.starting_time,
        )
        .label("other_timeoff_exists"),
    )

    info = (await db.execute(stmt)).one()

    if not info.works_today:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"you didn't say that you work today at this range, day {day_of_week} of the week from {timeoff_info.starting_time} to {finish_time}",
        )
    elif info.on_leave_schedule:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"you should be on a leave now.",
        )
    elif info.other_timeoff_exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"another timeoff interlaps with this one.",
        )

    elif info.any_special_schedule:

        stmt = select(
            exists(SpecialSchedules)
            .where(
                SpecialSchedules.user_id == user.id,
                SpecialSchedules.date == today,
                SpecialSchedules.starting_time <= timeoff_info.starting_time,
                SpecialSchedules.finish_time >= finish_time,
            )
            .label("does_work_at_that_time"),
            exists(SpecialRestTimes)
            .where(
                SpecialRestTimes.user_id == user.id,
                SpecialRestTimes.date == today,
                SpecialRestTimes.starting_time < finish_time,
                SpecialRestTimes.finish_time > timeoff_info.starting_time,
            )
            .label("doctor_schedule_to_rest_within"),
        )

        result = (await db.execute(stmt)).one()
        if not result.does_work_at_that_time:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "you set a special schedule where you don't work at the provided range.",
            )
        elif result.doctor_schedule_to_rest_within:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "you set a special schedule that today, and you scheduled a rest time which overlap with the range provided.",
            )

    reason = timeoff_info.reason
    existence_special_schedule_stmt = select(
        exists(TimeOffs).where(
            TimeOffs.user_id == user.id,
            TimeOffs.starting_time < finish_time,
            TimeOffs.finish_time > timeoff_info.starting_time,
        )
    )
    existing_leaves = await db.scalar(existence_special_schedule_stmt)

    if existing_leaves:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "you have scheduled to take time off within this range.",
        )

    timeoff = TimeOffs(
        user_id=user.id,
        starting_time=timeoff_info.starting_time,
        finish_time=finish_time,
        date=today,
        reason=reason,
    )

    db.add(timeoff)
    await db.commit()

    return timeoff


async def add_special_schedule(
    *, db: AsyncSession, user: User, special_schedule: SSSchema
):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    data = format_doctor_special_schedule(special_schedule, user.id)

    stmt = insert(SpecialSchedules).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "user_id"],
        set_={
            "starting_time": stmt.excluded.starting_time,
            "finish_time": stmt.excluded.finish_time,
            "is_vacation": stmt.excluded.is_vacation,
            "updated_at": now(),
            "max_appointments": stmt.excluded.max_appointments,
        },
    ).returning(SpecialSchedules)

    output = (await db.scalars(stmt)).all()
    await db.commit()

    return output


async def modify_special_rest_times(
    *, db: AsyncSession, user: User, rest_time: SRTSchema
):
    if not user.is_doctor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not authenticated as a doctor."
        )

    existence_stmt = select(
        exists().where(
            SpecialRestTimes.date == rest_time.date,
            SpecialRestTimes.user_id == user.id,
            SpecialRestTimes.starting_time < SpecialRestTimes.finish_time,
            SpecialRestTimes.finish_time > rest_time.starting_time,
        )
    )
    existence = await db.scalar(existence_stmt)

    if existence:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "there exists a special rest time that overlaps with this one.",
        )

    # data = format_special_doctor_rest_time(rest_time, user.id)
    stmt = (
        insert(SpecialRestTimes)
        .values(
            {
                "user_id": user.id,
                "starting_time": rest_time.starting_time,
                "finish_time": rest_time.finish_time,
                "date": rest_time.date,
                "reason": rest_time.reason,
            }
        )
        .returning(SpecialRestTimes)
    )
    try:
        output = (await db.scalars(stmt)).one()
        await db.commit()

    except IntegrityError as e:
        err_msg = str(e.orig).lower()

        if "special_rest_times_user_id_date_fkey" in err_msg:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"you didn't set your a special schedule for this day.",
            )

    return output


async def get_working_times(*, db: AsyncSession, doctor_id: UUID):
    stmt = select(
        exists().where(
            Users.id == doctor_id, Users.is_active.is_(True), Users.is_doctor.is_(True)
        )
    )

    doctor_exists = await db.scalar(stmt)

    if not doctor_exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this id matches no doctors.",
        )

    stmt = (
        select(WorkingDays)
        .where(WorkingDays.user_id == doctor_id)
        .options(selectinload(WorkingDays.rest_times))
    )

    working_days = (await db.scalars(stmt)).all()

    return working_days


async def fetch_special_schedules(
    *, db: AsyncSession, doctor_id: UUID, info: FetchSpecialSchedule
):
    stmt = select(
        exists().where(
            Users.id == doctor_id, Users.is_active.is_(True), Users.is_doctor.is_(True)
        )
    )

    doctor_exists = await db.scalar(stmt)

    if not doctor_exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this id matches no doctors.",
        )

    stmt = None
    # include_rest_time = (
    #     SpecialSchedules.date == info.date if info.date is not None else True
    # )
    condition = (SpecialSchedules.user_id == doctor_id) & (
        SpecialSchedules.date == info.date if info.date is not None else True
    )

    if info.include_rest_times:
        print("include")
        stmt = (
            select(SpecialSchedules)
            .where(condition)
            .options(selectinload(SpecialSchedules.rest_times))
        )
    else:
        stmt = select(SpecialSchedules).where(condition)

    special_schedule = (await db.scalars(stmt)).all()

    return special_schedule


async def fetch_leaves(*, db: AsyncSession, doctor_id: UUID, include_passed_ones: bool):
    stmt = select(
        exists().where(
            Users.id == doctor_id, Users.is_active.is_(True), Users.is_doctor.is_(True)
        )
    )

    doctor_exists = await db.scalar(stmt)

    if not doctor_exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this id matches no doctors.",
        )

    condition = None
    if include_passed_ones:
        condition = Leaves.user_id == doctor_id
    else:
        condition = (Leaves.user_id == doctor_id) & (Leaves.finish_date >= date.today())

    stmt = select(Leaves).where(condition)

    leaves = (await db.scalars(stmt)).all()

    return leaves


async def fetch_timeoffs(*, db: AsyncSession, doctor_id: UUID):
    stmt = select(
        exists().where(
            Users.id == doctor_id, Users.is_active.is_(True), Users.is_doctor.is_(True)
        )
    )

    doctor_exists = await db.scalar(stmt)

    if not doctor_exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this id matches no doctors.",
        )

    stmt = select(TimeOffs).where(
        TimeOffs.user_id == doctor_id, TimeOffs.date == date.today()
    )

    leaves = (await db.scalars(stmt)).all()

    return leaves


async def delete_working_day(*, db: AsyncSession, user: User, id: UUID):
    if not user.is_doctor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "you're not a doctor.")

    stmt = (
        delete(WorkingDays)
        .where(WorkingDays.id == id, WorkingDays.user_id == user.id)
        .returning(WorkingDays.id)
    )

    deleted = await db.scalar(stmt)
    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this working day doesn't exist or not yours.",
        )
    await db.commit()


async def delete_special_schedule(*, db: AsyncSession, user: User, id: UUID):
    if not user.is_doctor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "you're not a doctor.")

    stmt = (
        delete(SpecialSchedules)
        .where(SpecialSchedules.id == id, SpecialSchedules.user_id == user.id)
        .returning(SpecialSchedules.id)
    )

    deleted = await db.scalar(stmt)

    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this special schedule doesn't exist or not yours.",
        )
    await db.commit()


async def delete_leave(*, db: AsyncSession, user: User, id: UUID):

    if not user.is_doctor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "you're not a doctor.")

    stmt = (
        delete(Leaves)
        .where(Leaves.id == id, Leaves.user_id == user.id)
        .returning(Leaves.id)
    )

    deleted = await db.scalar(stmt)

    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this leave doesn't exist or not yours.",
        )
    await db.commit()


async def delete_timeoff(*, db: AsyncSession, user: User, id: UUID):

    if not user.is_doctor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "you're not a doctor.")

    stmt = (
        delete(TimeOffs)
        .where(TimeOffs.id == id, TimeOffs.user_id == user.id)
        .returning(TimeOffs.id)
    )

    deleted = await db.scalar(stmt)

    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "this time off doesn't exist or not yours.",
        )
    await db.commit()


async def add_service(*, db: AsyncSession, user: User, service_info: DoctorService):

    if not user.is_doctor:
        return HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not an authenticated doctor."
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=env.chargily_product_endpoint,
            headers={
                "Authorization": f"Bearer {env.chargily_secret_key}",
                "Content-Type": "application/json",
            },
            json={"name": service_info.name},
        )

        product_data = response.json()
        response = await client.post(
            url=env.chargily_price_endpoint,
            headers={
                "Authorization": f"Bearer {env.chargily_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "amount": service_info.price,
                "currency": "dzd",
                "product_id": product_data["id"],
            },
        )

        price_data = response.json()

    service = DoctorServices(
        doctor_id=user.id,
        name=service_info.name,
        price=service_info.price,
        description=service_info.description,
        chargily_pay_product_id=product_data["id"],
        chargily_pay_price_id=price_data["id"],
    )

    db.add(service)

    try:
        await db.commit()

    except IntegrityError as e:
        err_msg = str(e.orig)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "you already have a service with this name."
        )

    return service


async def get_doctor_services(*, db: AsyncSession, doctor_id: UUID):
    pass
    stmt = select(Users.is_doctor).where(
        Users.id == doctor_id, Users.is_active.is_(True)
    )

    is_doctor = await db.execute(stmt)
    is_doctor = is_doctor.scalar_one_or_none()

    if is_doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no users with this id.")

    if not is_doctor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user is not a doctor.")

    services_stmt = select(DoctorServices).where(DoctorServices.doctor_id == doctor_id)
    services = (await db.scalars(services_stmt)).all()

    return services


async def check_if_doctor_is_free(*, db: AsyncSession, info: IsDoctorFree):
    day_of_week = info.date.weekday()

    # appointments_count_stmt = select(func.count()).where(
    #     Appointments.service_id == info.service_id,
    #     Appointments.date == info.date,
    #     Appointments.status == AppointmentStatus.scheduled.value,
    # )
    # in_process_count_stmt = select(func.count()).where(
    #     AppointmentPaymentSession.service_id == info.service_id,
    #     AppointmentPaymentSession.created_at <= now(),
    #     AppointmentPaymentSession.expires_at >= now(),
    #     AppointmentPaymentSession.is_expired == False,
    # )

    stmt = (
        select(Users.id, Users.is_active)
        .join(DoctorServices.user)
        .where(DoctorServices.id == info.service_id)
    )

    tmp = (await db.execute(stmt)).one_or_none()

    if tmp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no doctor services matching that id."
        )

    doctor_id, still_active = tmp

    if not still_active:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no doctor services matching that id."
        )

    appointments_count_stmt = select(func.count()).where(
        Appointments.doctor_id == doctor_id,
        Appointments.date == info.date,
        Appointments.status == AppointmentStatus.scheduled.value,
    )
    in_process_count_stmt = select(func.count()).where(
        AppointmentPaymentSession.service_id.in_(
            select(DoctorServices.id).where(DoctorServices.doctor_id == doctor_id)
        ),
        AppointmentPaymentSession.created_at <= now(),
        AppointmentPaymentSession.expires_at >= now(),
        AppointmentPaymentSession.is_expired == False,
    )
    #

    appointments_count = await db.scalar(appointments_count_stmt)
    in_process_count = await db.scalar(in_process_count_stmt)

    special_schedule_subquery = select(
        (
            exists().where(
                SpecialSchedules.date == info.date,
                SpecialSchedules.user_id == doctor_id,
            )
        )
    ).scalar_subquery()

    leave_subquery = select(
        (
            exists().where(
                Leaves.starting_date <= info.date,
                Leaves.finish_date >= info.date,
                Leaves.user_id == doctor_id,
            )
        )
    ).scalar_subquery()

    stmt = select(special_schedule_subquery, leave_subquery)

    data = (await db.execute(stmt)).one()

    special_schedule_exists, on_leave = data

    if special_schedule_exists:

        special_schedule_stmt = select(SpecialSchedules).where(
            SpecialSchedules.user_id == doctor_id, SpecialSchedules.date == info.date
        )
        special_schedule = (await db.scalars(special_schedule_stmt)).one()

        if special_schedule.is_vacation == True:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "doctor is on vacation that day."
            )
        if special_schedule.max_appointments <= appointments_count:  # type:ignore
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "doctor has reached the maximum number of appointments per day.",
            )
        if (
            special_schedule.max_appointments
            <= appointments_count + in_process_count  # type:ignore
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "doctor has some appointments payments in process, try later.",
            )

    if on_leave:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "doctor is on a leave.")
    else:
        stmt = select(WorkingDays).where(
            WorkingDays.user_id == doctor_id, WorkingDays.day_of_week == day_of_week
        )
        working_day_info = (await db.scalars(stmt)).one_or_none()

        if working_day_info is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "the doctor doesn't work on that day.",
            )

        if working_day_info.max_appointments <= appointments_count:  # type:ignore
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "the doctor has reached the maximum number of appointments on that day for this service.",
            )
        if (
            working_day_info.max_appointments
            <= appointments_count + in_process_count  # type:ignore
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "some appointment payments are in process, try later.",
            )
