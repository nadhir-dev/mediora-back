from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from starlette import status

from src.models.users import Info, Users
from src.schemas.users import UpdateUser

from sqlalchemy.ext.asyncio import AsyncSession


async def update_user_data(db_session: AsyncSession, user: Users, updates: UpdateUser):

    updates_dict = updates.model_dump(exclude_none=True)
    users_table_fields = {"first_name", "last_name", "username"}
    info_table_fields = {"phone", "gender", "date_of_birth"}

    info_table_updates = {}
    for k, v in updates_dict.items():
        if k in users_table_fields:
            setattr(user, k, v)
        elif k in info_table_fields:
            info_table_updates[k] = v

    try:
        if len(info_table_updates):

            stmt = update(Info).values(**info_table_updates).where(Info.id == user.id)
            await db_session.execute(stmt)

        await db_session.commit()
    except IntegrityError as e:
        err_msg = str(e.orig).lower()

        corresponding_field = "username" if "users_username_key" in err_msg else "phone"

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"this {corresponding_field} already exists."
        )

    return user
