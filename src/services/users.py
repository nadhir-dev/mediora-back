from datetime import UTC, datetime

from fastapi import HTTPException, Request
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import update, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from starlette import status

from src.config.env import env
from src.models.doctor_authentication import Media
from src.models.users import Info, ProfileMedia, Users, Auth
from src.schemas.doctor_requests import ImageFile
from src.schemas.users import UpdateUser, UserFlatResponse

from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.authentication import gen_id, get_token


async def update_user_data(*, db: AsyncSession, user: Users, updates: UpdateUser):

    updates_dict = updates.model_dump(exclude_none=True)
    users_table_fields = {"first_name", "last_name", "username"}
    info_table_fields = {
        "phone",
        "gender",
        "date_of_birth",
        "description",
        "clinic_posy",
        "clinic_posx",
    }
    doctor_fields = {"description", "clinic_posy", "clinic_posx"}

    # if not user.is_doctor and updates.description:
    #     raise HTTPException(
    #         status.HTTP_400_BAD_REQUEST, "only doctors can change their description."
    #     )
    # if not user.is_doctor and (updates.clinic_posy or updates.clinic_posx):
    #     raise HTTPException(
    #         status.HTTP_400_BAD_REQUEST,
    #         "only doctors can change their clinic coordinates.",
    #     )

    if not user.is_doctor and any(
        getattr(updates, field) is not None for field in doctor_fields
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"only doctors can change the following: {doctor_fields}.",
        )

    info_table_updates = {}
    for k, v in updates_dict.items():
        if k in users_table_fields:
            setattr(user, k, v)
        elif k in info_table_fields:
            info_table_updates[k] = v

    try:
        if len(info_table_updates):

            stmt = update(Info).values(**info_table_updates).where(Info.id == user.id)
            await db.execute(stmt)

        await db.commit()
    except IntegrityError as e:
        err_msg = str(e.orig).lower()

        corresponding_field = "username" if "users_username_key" in err_msg else "phone"

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"this {corresponding_field} already exists."
        )

    return user


async def add_profile_picture(*, db: AsyncSession, user: Users, picture: ImageFile):

    media = Media(
        id=gen_id(),
        url=picture.secure_url,
        public_id=picture.public_id,
        resource_type=picture.resource_type,
        format=picture.format,
    )
    profile = ProfileMedia(user_id=user.id, document_id=media.id)

    user.picture = picture.secure_url

    db.add_all([media, profile])

    await db.commit()

    return user


async def get_user_data(*, db: AsyncSession, request: Request):
    token = get_token(request)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing token.",
        )

    try:
        decoded = jwt.decode(token, env.jwt_secret, algorithms="HS256")

    except (JWTError, ExpiredSignatureError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token or has expired.",
        )

    stmt = (
        select(Users)
        .where(Users.id == decoded["id"])
        .options(
            joinedload(Users.auth).load_only(Auth.last_password_reset),
            joinedload(Users.info),
        )
    )

    user = (await db.scalars(stmt)).one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials.",
        )

    iat = datetime.fromtimestamp(decoded["exp"] - 60 * 15, UTC)  # type ignore

    if user.auth.last_password_reset > iat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="you changed you're password lately, please login again.",
        )
    response = UserFlatResponse(
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
    )
    return response
