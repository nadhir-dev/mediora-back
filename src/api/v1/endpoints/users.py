from typing import Annotated, Any
from fastapi import APIRouter, Body, Depends, Response
from src.db.connection import get_db
from src.schemas.users import UpdateUser, User
from src.services.authentication import protect
from src.services.users import update_user_data

from sqlalchemy.ext.asyncio import AsyncSession


users_router = APIRouter(prefix="/users")


@users_router.patch("/me")
async def update_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Any, Depends(protect)],
    updates: Annotated[UpdateUser, Body()],
    response: Response,
) -> User:

    user = await update_user_data(db_session=db, user=user, updates=updates)

    return user
