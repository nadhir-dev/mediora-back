from datetime import datetime, UTC, timedelta


def after(minutes: int | None = None, days: int | None = None) -> datetime:
    time = datetime.now(UTC)

    if minutes:
        time += timedelta(minutes=minutes)
    if days:
        time += timedelta(days=days)

    return time


def now():
    return datetime.now(UTC)
