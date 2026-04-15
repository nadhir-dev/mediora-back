from curses import reset_prog_mode
from typing import Annotated
from fastapi import APIRouter, Response, Request, HTTPException, status
from fastapi.params import Depends, Body, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.background import BackgroundTasks

from src.config.env import env, production
from src.config.http import limiter
from src.db import get_db
from src.schemas.users import (
    ExistsCheckResponse,
    TokenWithMessage,
    ResetPassword,
    SuccessMessage,
    AccessToken,
    User,
    UserInsertion,
    Email,
    Password,
    SigninCredentials,
    Username,
)
from src.services.authentication import (
    change_password,
    check_username_existence,
    protect,
    reset_password,
    signup,
    signin,
    forgot_password,
    logout_user,
    old_reset_password,
    send_email_verification_otp,
    update_password_with_token,
    verify_otp_code_and_email,
    signin_with_google,
    rotate_refresh_token,
)
from src.config.google_client import oauth
from src.utils.authentication import (
    get_credentials,
    get_device_id,
    get_token,
    get_creation_token,
)

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/check-email", response_model=SuccessMessage)
@limiter.limit("2/minute")
async def verify_email(
    session: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[Email, Body(embed=True)],
    background: BackgroundTasks,
    request: Request,
):
    await send_email_verification_otp(bg=background, db=session, email=email)

    return {"message": "the otp code was scheduled, check your mailbox."}


@auth_router.post("/check-username", response_model=ExistsCheckResponse)
async def check_if_username_exists(
    session: Annotated[AsyncSession, Depends(get_db)],
    username: Annotated[Username, Body(embed=True)],
):
    exists = await check_username_existence(db=session, username=username)

    return {"exists": exists}


@auth_router.get("/verify-email", response_model=TokenWithMessage)
async def activate_email(
    session: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str, Query()],
    email: Annotated[str, Query()],
    res: Response,
):
    token = await verify_otp_code_and_email(db=session, email=email, code=code)

    res.headers["Creation-Token"] = token
    res.set_cookie(
        "creation_token",
        token,
        samesite="none",
        httponly=True,
        secure=production,
        expires=env.creation_token_expiration,
    )

    return {
        "message": "this token will expires in 30 minutes.",
        "token": token,
    }


@auth_router.post("/signup", response_model=AccessToken)
async def register(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_in: Annotated[UserInsertion, Body()],
    request: Request,
    res: Response,
):
    device_id = get_device_id(request=request, generate=True)
    creation_token = get_creation_token(request=request)

    refresh_token, access_token, device_id = await signup(
        db=session,
        user_data=user_in,
        device_id=device_id,  # type:ignore
        creation_token=creation_token,
    )

    res.set_cookie(
        "access_token",
        access_token,
        secure=production,
        max_age=env.access_token_expiration,
        samesite="none",
        httponly=True,
    )
    res.set_cookie(
        "refresh_token",
        refresh_token,
        secure=production,
        max_age=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
    )

    res.set_cookie(
        "device_id",
        device_id,
        secure=production,
        max_age=env.forever,
        samesite="none",
        httponly=True,
    )

    res.headers["access_token"] = access_token
    res.headers["refresh_token"] = refresh_token
    res.headers["X-Device-Id"] = str(device_id)
    res.status_code = status.HTTP_201_CREATED

    return {"token": access_token, "type": "Bearer"}


@auth_router.post("/signin", response_model=AccessToken)
async def login(
    credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    res: Response,
):
    device_id = get_device_id(request, generate=True)

    refresh_token, access_token = await signin(
        db=session,
        credentials=get_credentials(
            identifier=credentials.username, password=credentials.password
        ),
        device_id=device_id,  # type: ignore
    )

    res.set_cookie(
        "access_token",
        access_token,
        secure=production,
        max_age=env.access_token_expiration,
        samesite="none",
        httponly=True,
    )
    res.set_cookie(
        "refresh_token",
        refresh_token,
        secure=production,
        max_age=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
    )

    res.set_cookie(
        "device_id",
        str(device_id),
        secure=production,
        max_age=env.forever,
        samesite="none",
        httponly=True,
    )

    res.headers["access_token"] = access_token
    res.headers["refresh_token"] = refresh_token
    res.headers["X-Device-Id"] = str(device_id)

    return {"token": access_token, "type": "Bearer"}


@auth_router.delete("/signout")
async def logout(
    session: Annotated[AsyncSession, Depends(get_db)], request: Request, res: Response
):

    device_id = get_device_id(request, required=True)
    refresh_token = get_token(request, token_type="refresh", required=True)

    await logout_user(
        db=session, refresh_token=refresh_token, device_id=device_id  ## type:ignore
    )
    res.status_code = status.HTTP_204_NO_CONTENT

    res.delete_cookie("refresh_token")
    res.delete_cookie("access_token")


# Redirect user to Google for authentication
@auth_router.get("/google")
async def redirect_to_google(request: Request):
    return await oauth.google.authorize_redirect(  # type: ignore
        request, redirect_uri=env.google_redirect_url
    )


@auth_router.get("/google/callback", response_model=AccessToken)
async def auth_google(
    session: Annotated[AsyncSession, Depends(get_db)], request: Request, res: Response
):
    device_id = get_device_id(request)
    try:
        token = await oauth.google.authorize_access_token(request)  # type:ignore
    except Exception:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "session has ended try again."
        )

    refresh_token, access_token, device_id = await signin_with_google(
        db=session, token=token, device_id=device_id
    )

    res.set_cookie(
        "access_token",
        access_token,
        secure=production,
        max_age=env.access_token_expiration,
        samesite="none",
        httponly=True,
    )
    res.set_cookie(
        "refresh_token",
        refresh_token,
        secure=production,
        max_age=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
    )
    res.set_cookie(
        "device_id",
        device_id,
        secure=production,
        max_age=env.forever,
        samesite="none",
        httponly=True,
    )
    res.headers["X-Device-Id"] = str(device_id)

    res.headers["access_token"] = access_token
    res.headers["refresh_token"] = refresh_token
    res.status_code = status.HTTP_201_CREATED

    return {"token": access_token, "type": "Bearer"}


@auth_router.post("/forgot-password", response_model=SuccessMessage)
@limiter.limit("2/minute")
async def send_reset_password_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[Email, Body(embed=True)],
    tasks: BackgroundTasks,
    request: Request,
):

    await forgot_password(db=session, tasks=tasks, email=email)

    return {"message": "otp code was sent, check your mailbox."}


@auth_router.post("/reset-password", response_model=TokenWithMessage)
@limiter.limit("5/minute")
async def verify_reset_password_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str, Body(embed=True)],
    request: Request,
):
    reset_token = await reset_password(db=session, code=code)

    return {"message": "this token expires after 30 minutes.", "token": reset_token}


@auth_router.patch("/update-password-with-token", response_model=AccessToken)
@limiter.limit("5/minute")
async def change_password_with_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    body: Annotated[ResetPassword, Body()],
    request: Request,
    response: Response,
):
    device_id = get_device_id(request=request)
    refresh_token, access_token = await update_password_with_token(
        db=session, data=body, device_id=device_id
    )

    response.set_cookie(
        "access_token",
        access_token,
        expires=env.access_token_expiration,
        samesite="none",
        httponly=True,
        secure=production,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        secure=production,
        expires=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
    )
    response.headers["access_token"] = access_token
    response.headers["refresh_token"] = refresh_token

    return {"token": access_token, "type": "Bearer"}


@auth_router.post("/refresh", response_model=AccessToken)
async def refresh(
    session: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    response: Response,
):
    device_id = get_device_id(request=request, required=True)
    old_refresh_token = get_token(request=request, token_type="refresh", required=True)

    refresh_token, access_token = await rotate_refresh_token(
        db=session, refresh_token=old_refresh_token, device_id=device_id  # type:ignore
    )
    response.set_cookie(
        "access_token",
        access_token,
        expires=env.access_token_expiration,
        samesite="none",
        httponly=True,
        secure=production,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        expires=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
        secure=production,
    )

    response.headers["access_token"] = access_token
    response.headers["refresh_token"] = refresh_token
    return {"token": access_token, "type": "Bearer"}


@auth_router.patch("/change-password", response_model=AccessToken)
async def update_password(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    password: Annotated[Password, Body(embed=True)],
    current_password: Annotated[Password, Body(embed=True)],
    request: Request,
    response: Response,
):
    device_id = get_device_id(request, required=True)
    refresh_token, access_token = await change_password(
        db=session, device_id=device_id, user=user, current_password=current_password, new_password=password  # type: ignore
    )

    response.set_cookie(
        "access_token",
        access_token,
        expires=env.access_token_expiration,
        samesite="none",
        httponly=True,
        secure=production,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        expires=env.refresh_token_expiration,
        samesite="none",
        httponly=True,
        secure=production,
    )

    response.headers["access_token"] = access_token
    response.headers["refresh_token"] = refresh_token
    return {"token": access_token, "type": "Bearer"}
