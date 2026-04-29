from typing import Any, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.config.env import env


engine = create_async_engine(
    env.db_url,
    connect_args={"statement_cache_size": 0},
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


class BASE(DeclarativeBase):
    pass


async def init_db():
    import src.models.users
    import src.models.doctor_authentication
    import src.models.doctor_schedule
    import src.models.messaging
    import src.models.Appointments
    import src.models.feedback

    #

    async with engine.begin() as conn:
        pass


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        yield session
