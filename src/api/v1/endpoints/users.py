from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Body, Depends
from fastapi import Request
from fastapi.responses import FileResponse
from src.db.connection import get_db
from src.models.users import Users
from src.schemas.doctor_requests import ImageFile
from src.schemas.users import (
    ExtendedUserResponse,
    UpdateUser,
    UserResponse,
)
from src.services.authentication import protect
from src.services.users import add_profile_picture, get_user_data, update_user_data

from sqlalchemy.ext.asyncio import AsyncSession

users_router = APIRouter(prefix="/users")


@users_router.patch("/me", response_model=UserResponse)
async def update_profile(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Users, Depends(protect)],
    updates: Annotated[UpdateUser, Body()],
):

    user = await update_user_data(db=session, user=user, updates=updates)

    return {"data": user}


@users_router.get("/me", response_model=ExtendedUserResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):

    user = await get_user_data(db=session, request=request)

    return {"data": user}


@users_router.post("/profile", response_model=UserResponse)
async def upload_profile_picture(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Users, Depends(protect)],
    picture: Annotated[ImageFile, Body()],
):

    user = await add_profile_picture(db=session, user=user, picture=picture)

    return {"data": user}
