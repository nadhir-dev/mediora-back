from typing import Annotated, TYPE_CHECKING, Any
from datetime import datetime, UTC
from uuid import UUID
from fastapi import Request
from jose import jwt, JWTError, ExpiredSignatureError
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, update, insert, exists
from sqlalchemy.ext.asyncio import AsyncSession
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from src.models.users import Users, Auth, Info, Sessions, PendingEmails
from src.schemas.users import (
    ResetPassword,
    UserInsertion,
    SigninCredentials,
    Email,
    Username,
)
from src.config.env import env
from src.utils.authentication import (
    get_token,
    parse_google_provided_data,
)
from src.utils.helpers import (
    get_user_from_cache,
    remove_user_from_cache,
    save_user_in_cache,
    serialize_sqlalchemy,
    user_dict_to_object,
)
from src.utils.time import now, after

from src.db import get_db
from src.utils.authentication import infer_identifier_type, format_data
from src.utils.authentication import (
    gen_id,
    gen_access_token,
    gen_refresh_token,
    gen_token,
    hash_token,
    gen_random_code,
)

from src.integrations.mailing import (
    send_password_reset_token_email,
    send_email_verification_otp_code,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi.background import BackgroundTasks

ag2 = PasswordHasher()


async def signup(
    *, db: AsyncSession, user_data: UserInsertion, device_id: str, creation_token: str
):
    email_verified_stmt = select(PendingEmails).where(
        PendingEmails.is_verified == True,
        PendingEmails.token == hash_token(creation_token),
    )

    email_verified = (await db.scalars(email_verified_stmt)).one_or_none()

    if not email_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token.")

    if not email_verified.token_expires > now():  # type: ignore
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "expired token, verify the ownership of this email to get a new one.",
        )

    data = format_data(user_data, device_id=device_id)

    data.auth_table["password"] = ag2.hash(data.auth_table["password"])

    try:
        user_out = Users(**data.user_table)
        auth = Auth(**data.auth_table)
        info = Info(**data.info_table)
        session = Sessions(**data.session_table)

        db.add_all([user_out, auth, info, session])
        await db.commit()

    except IntegrityError as e:
        await db.rollback()
        msg = str(e.orig).lower()

        if "users_username_key" in msg:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "a user with this username already exists."
            )
        elif "info_phone_key" in msg:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "a user with this phone number already exists.",
            )
        else:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "data provided is contradictory."
            )

    else:
        await db.delete(email_verified)

    access_token = gen_access_token(user_out.id)

    return session.refresh_token, access_token, session.device_id


async def signin(*, db: AsyncSession, credentials: SigninCredentials, device_id: str):
    credential = (
        Users.username
        if infer_identifier_type(identifier=credentials.identifier) == "username"
        else Users.email
    )

    stmt = select(Auth).where(Auth.user.has(credential == credentials.identifier))

    result = await db.scalars(stmt)
    user_auth = result.one_or_none()

    if user_auth is None:

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    if user_auth.password is None:

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "you didn't add this method of logging in, try google oauth instead.",
        )

    try:
        ag2.verify(hash=user_auth.password, password=credentials.password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    access_token = gen_access_token(user_auth.id)
    refresh_token = gen_refresh_token()

    update_stmt = (
        update(Sessions)
        .values(invoked_at=now())
        .where(
            Sessions.device_id == device_id,
            Sessions.invoked_at == None,
            Sessions.user_id == user_auth.id,
        )
    )

    insert_stmt = insert(Sessions).values(
        refresh_token=refresh_token,
        refresh_token_expires=after(days=60),
        device_id=device_id,
        # auth_id=user_auth.id,
        user_id=user_auth.id,
    )

    await db.execute(update_stmt)
    await db.execute(insert_stmt)

    await db.commit()

    return refresh_token, access_token


async def logout_user(*, db: AsyncSession, refresh_token: str, device_id: str):

    stmt = select(Sessions).where(
        Sessions.refresh_token == refresh_token, Sessions.device_id == device_id
    )

    session = (await db.scalars(stmt)).one_or_none()

    if not session:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid information provided, can't logout."
        )

    if session.invoked_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session already revoked.")

    session.invoked_at = datetime.now()
    await db.commit()


async def signin_with_google(*, db: AsyncSession, token, device_id: str | None):

    user_info = token.get("userinfo", dict())
    user_data = parse_google_provided_data(user_info)
    email = user_data.email

    device_id_sent = device_id is not None
    device_id = device_id if device_id_sent else str(gen_id())

    if not email:
        # can happen in some enterprise gmails
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="missing email."
        )

    if not user_info.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot sign up with unverified email.",
        )

    refresh_token = gen_refresh_token()

    stmt = select(Users, Auth).join(Auth).where(Users.email == email)
    result = (await db.execute(stmt)).one_or_none()

    if not result:

        user = Users(
            **user_data.model_dump(exclude={"google_open_id"}, exclude_none=True)
        )
        auth = Auth(id=user_data.id, google_open_id=user_data.google_open_id)
        session = Sessions(
            device_id=device_id,
            # auth_id=user_data.id,
            user_id=user_data.id,
            refresh_token=refresh_token,
            refresh_token_expires=after(days=60),
        )
        info = Info(id=user_data.id)

        db.add_all([user, auth, info, session])

    else:
        user, auth = result

        if device_id_sent:
            update_stmt = (
                update(Sessions)
                .values(invoked_at=now())
                .where(
                    Sessions.device_id == device_id,
                    Sessions.invoked_at == None,
                    Sessions.user_id == user.id,
                )
            )
            await db.execute(update_stmt)

        session_stmt = insert(Sessions).values(
            device_id=device_id,
            user_id=user.id,
            refresh_token=refresh_token,
            refresh_token_expires=after(days=60),
        )
        update_stmt = (
            update(Auth)
            .where(Auth.id == user.id, Auth.google_open_id == None)
            .values(google_open_id=user_data.google_open_id)
        )

        await db.execute(update_stmt)
        await db.execute(session_stmt)

    await db.commit()

    return refresh_token, gen_access_token(user.id), device_id


async def reset_password(*, db: AsyncSession, code: str):

    # should be using tokens instead of otp code
    stmt = select(Auth).where(
        Auth.otp_code == code,
        Auth.otp_code_purpose == "forgot password",
        Auth.otp_code_expires > datetime.now(UTC),
    )

    user_auth = (await db.scalars(stmt)).one_or_none()

    if not user_auth:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token or has expired."
        )

    reset_token = gen_token()
    user_auth.reset_token = hash_token(reset_token)
    user_auth.reset_token_purpose = "reset password"
    user_auth.reset_token_expires = after(minutes=30)

    await db.commit()

    return reset_token


async def update_password_with_token(
    *, db: AsyncSession, data: ResetPassword, device_id: str | None, request: Request
):
    hashed_token = hash_token(data.reset_token)

    stmt = select(Auth).where(
        Auth.reset_token == hashed_token,
        Auth.reset_token_purpose == "reset password",
        Auth.reset_token_expires > datetime.now(UTC),
    )

    user_auth = (await db.scalars(stmt)).one_or_none()

    if not user_auth:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token or has expired."
        )

    refresh_token, access_token = gen_refresh_token(), gen_access_token(user_auth.id)

    user_auth.password = ag2.hash(data.password)
    user_auth.reset_token = user_auth.reset_token_expires = (
        user_auth.reset_token_purpose
    ) = None

    if device_id:
        update_stmt = (
            update(Sessions)
            .values(invoked_at=now())
            .where(
                Sessions.device_id == device_id,
                Sessions.invoked_at == None,
                Sessions.user_id == user_auth.id,
            )
        )
        await db.execute(update_stmt)

    insert_stmt = insert(Sessions).values(
        refresh_token=refresh_token,
        refresh_token_expires=after(days=60),
        device_id=device_id if device_id else str(gen_id()),
        user_id=user_auth.id,
    )

    await db.execute(insert_stmt)

    await db.commit()

    user_id = user_auth.id
    redis_key = f"user:{user_id}"
    await remove_user_from_cache(request.app.state.redis, redis_key)

    return refresh_token, access_token


async def old_reset_password(
    *, db: AsyncSession, token: str, password: str, device_id: str | None
):

    hashed_token = hash_token(token)

    stmt = select(Auth).where(
        Auth.reset_token == hashed_token,
        Auth.reset_token_purpose == "forgot password",
        Auth.reset_token_expires > datetime.now(UTC),
    )

    user_auth = (await db.scalars(stmt)).one_or_none()

    if not user_auth:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token or has expired."
        )

    refresh_token, access_token = gen_refresh_token(), gen_access_token(user_auth.id)

    user_auth.password = ag2.hash(password)
    user_auth.reset_token = user_auth.reset_token_expires = (
        user_auth.reset_token_purpose
    ) = None

    if device_id:
        update_stmt = (
            update(Sessions)
            .values(invoked_at=now())
            .where(
                Sessions.device_id == device_id,
                Sessions.invoked_at == None,
                Sessions.user_id == user_auth.id,
            )
        )
        await db.execute(update_stmt)

    insert_stmt = insert(Sessions).values(
        refresh_token=refresh_token,
        refresh_token_expires=after(days=60),
        device_id=device_id if device_id else str(gen_id()),
        # auth_id=user_auth.id,
        user_id=user_auth.id,
    )

    await db.execute(insert_stmt)

    await db.commit()

    return refresh_token, access_token


async def check_username_existence(*, db: AsyncSession, username: Username):
    stmt = select(exists().where(Users.username == username))
    username_exists = await db.scalar(stmt)
    return username_exists


async def forgot_password(*, db: AsyncSession, tasks: "BackgroundTasks", email: str):
    stmt = select(Auth).join(Auth.user).where(Users.email == email)
    user = (await db.scalars(stmt)).one_or_none()

    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "there is no user with this email."
        )

    if not user.password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "unallowed.")

    code = gen_random_code(10)

    tasks.add_task(send_password_reset_token_email, email, code)

    user.otp_code = code
    user.otp_code_purpose = "forgot password"
    user.otp_code_expires = after(minutes=10)

    await db.commit()


async def protect(db: Annotated[AsyncSession, Depends(get_db)], request: Request):
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
    user_id = decoded["id"]

    redis_key = f"user:{user_id}"

    cache = await get_user_from_cache(request.app.state.redis, redis_key)
    if cache:

        lpr = datetime.fromisoformat(cache["last_password_reset"])
        del cache["last_password_reset"]
        print("cache hit")
        user = user_dict_to_object(cache)
    else:

        stmt = (
            select(Users, Auth.last_password_reset)
            .join(Users.auth)
            .where(Users.id == user_id)
        )

        data = (await db.execute(stmt)).one_or_none()

        if not data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials.",
            )
        user, lpr = data

        user_to_cache = {
            **serialize_sqlalchemy(user),
            "last_password_reset": lpr.isoformat(),
        }
        await save_user_in_cache(request.app.state.redis, redis_key, user_to_cache)

    iat = datetime.fromtimestamp(decoded["exp"] - 60 * 15, UTC)  # type ignore

    if lpr > iat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="you changed you're password lately, please login again.",
        )

    return user


async def send_email_verification_otp(
    *, db: AsyncSession, bg: "BackgroundTasks", email: Email
):

    stmt = select(exists(Users.email).where(Users.email == email))

    user_exists = await db.scalar(stmt)

    if user_exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "a user with this email already exists."
        )

    code = gen_random_code()

    insert_stmt = insert(PendingEmails).values(
        email=email,
        code=code,
        code_issued=now(),
        code_expires=after(minutes=15),
    )

    try:
        await db.execute(insert_stmt)

    except IntegrityError:
        await db.rollback()

        update_stmt = (
            update(PendingEmails)
            .where(
                PendingEmails.email == email,
            )
            .values(
                code=code,
                code_issued=now(),
                code_expires=after(minutes=15),
            )
        )
        await db.execute(update_stmt)

    await db.commit()
    bg.add_task(send_email_verification_otp_code, email=email, code=code)


async def verify_otp_code_and_email(*, db: AsyncSession, email: Email, code: str):

    stmt = select(PendingEmails).where(
        PendingEmails.email == email,
        PendingEmails.code == code,
        PendingEmails.code_expires > now(),
    )

    result = (await db.scalars(stmt)).one_or_none()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid code or has expired.",
        )

    token = gen_token()
    hashed_token = hash_token(token)

    result.code_expires = result.code_issued = result.code = None
    result.token = hashed_token
    result.token_issued = now()
    result.token_expires = after(minutes=30)
    result.is_verified = True

    await db.commit()

    return token


async def rotate_refresh_token(*, db: AsyncSession, refresh_token: str, device_id: str):

    stmt = select(Sessions).where(
        Sessions.device_id == device_id, Sessions.refresh_token == refresh_token
    )

    session = (await db.scalars(stmt)).one_or_none()

    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token.")

    if session.invoked_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session already invoked.")

    if session.refresh_token_expires < now():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired, login.")

    user_id = session.user_id
    new_refresh_token = gen_refresh_token()

    new_session = Sessions(
        user_id=user_id,
        # auth_id=user_id,
        id=gen_id(),
        refresh_token=new_refresh_token,
        refresh_token_expires=after(days=60),
        device_id=device_id,
    )

    session.invoked_at = now()
    db.add(new_session)

    await db.commit()

    access_token = gen_access_token(user_id)

    return new_refresh_token, access_token


async def change_password(
    *,
    db: AsyncSession,
    device_id: str,
    user: Any,
    current_password: str,
    new_password: str,
    request: Request,
):
    stmt = select(Auth).where(Auth.id == user.id)
    auth = (await db.scalars(stmt)).one()

    try:
        ag2.verify(auth.password, current_password)  # type: ignore
    except (VerifyMismatchError, VerificationError, InvalidHashError):

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials.")

    auth.password = ag2.hash(new_password)
    auth.last_password_reset = now()

    expired_sessions_stmt = (
        update(Sessions)
        .values(invoked_at=now())
        .where(
            Sessions.invoked_at.is_(None),
            Sessions.device_id == device_id,
            Sessions.user_id == auth.id,
        )
    )

    refresh_token = gen_refresh_token()

    new_session_stmt = insert(Sessions).values(
        refresh_token=refresh_token,
        refresh_token_expires=after(days=60),
        device_id=device_id,
        user_id=user.id,
    )

    await db.execute(expired_sessions_stmt)
    await db.execute(new_session_stmt)

    await db.commit()

    user_id = auth.id
    redis_key = f"user:{user_id}"
    await remove_user_from_cache(request.app.state.redis, redis_key)

    return refresh_token, gen_access_token(user.id)
