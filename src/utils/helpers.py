from datetime import datetime
import json
from typing import Any, List

from src.config.env import env
from src.schemas.doctor_schedule import WorkingDays as WKSchema
from src.schemas.doctor_schedule import RestTimes as RTSchema
from src.schemas.doctor_schedule import SpecialSchedules as SSSchema
from src.schemas.doctor_schedule import SpecialRestTimes as SRTSchema

from src.utils.authentication import gen_id

from uuid import UUID

from redis import Redis


def format_doctor_schedule(s: WKSchema, user_id: UUID):

    if isinstance(s.schedule, list):

        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "day_of_week": v.day_of_week,
                "max_appointments": v.max_appointments,
                "starting_time": v.starting_time,
                "finish_time": v.finish_time,
            }
            for v in s.schedule
        ]

    else:
        # isinstance(s.schedule, WKSchema)
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "day_of_week": i,
                "max_appointments": s.schedule.schedule.max_appointments,
                "starting_time": s.schedule.schedule.starting_time,
                "finish_time": s.schedule.schedule.finish_time,
            }
            for i in range(s.schedule.start, s.schedule.end + 1)
        ]


def format_doctor_rest_time(s: RTSchema, user_id: UUID):

    if isinstance(s.schedule, List):
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "day_of_week": v.day_of_week,
                "starting_time": v.starting_time,
                "finish_time": v.finish_time,
                "reason": v.reason if hasattr(v, "reason") else None,
            }
            for v in s.schedule
        ]

    else:
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "day_of_week": i,
                "starting_time": s.schedule.rest.starting_time,
                "finish_time": s.schedule.rest.finish_time,
                "reason": (
                    s.schedule.rest.reason
                    if hasattr(s.schedule.rest, "reason")
                    else None
                ),
            }
            for i in range(s.schedule.start, s.schedule.end + 1)
        ]


def format_doctor_special_schedule(s: SSSchema, user_id: UUID):

    if isinstance(s.schedule, List):

        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "date": v.date,
                "max_appointments": v.max_appointments,
                "is_vacation": v.is_vacation,
                "starting_time": v.starting_time,
                "finish_time": v.finish_time,
            }
            for v in s.schedule
        ]

    else:
        # isinstance(s.schedule, WKSchema)
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "date": s.schedule.schedule.date,
                "is_vacation": s.schedule.schedule.is_vacation,
                "max_appointments": s.schedule.schedule.max_appointments,
                "starting_time": s.schedule.schedule.starting_time,
                "finish_time": s.schedule.schedule.finish_time,
            }
            for i in range(s.schedule.start, s.schedule.end + 1)
        ]


def format_special_doctor_rest_time(s: SRTSchema, user_id: UUID):

    if isinstance(s.schedule, List):
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "date": v.date,
                "starting_time": v.starting_time,
                "finish_time": v.finish_time,
                "reason": v.reason if hasattr(v, "reason") else None,
            }
            for v in s.schedule
        ]

    else:
        return [
            {
                "id": gen_id(),
                "user_id": user_id,
                "date": s.schedule.rest.date,
                "starting_time": s.schedule.rest.starting_time,
                "finish_time": s.schedule.rest.finish_time,
                "reason": (
                    s.schedule.rest.reason
                    if hasattr(s.schedule.rest, "reason")
                    else None
                ),
            }
            for i in range(s.schedule.start, s.schedule.end + 1)
        ]


def serialize_sqlalchemy(obj):
    data = {}

    for c in obj.__table__.columns:
        value = getattr(obj, c.name)

        if isinstance(value, UUID):
            value = str(value)

        elif isinstance(value, datetime):
            value = value.isoformat()

        data[c.name] = value

    return data


async def save_user_in_cache(redis: Redis, key: str, value: Any):
    await redis.set(
        key,
        json.dumps(value),
        ex=env.access_token_expiration,
    )


async def get_user_from_cache(redis: Redis, key: str):
    value = await redis.get(key)
    if value is None:
        return None

    return json.loads(value)


async def remove_user_from_cache(redis: Redis, key: str):
    await redis.delete(key)
