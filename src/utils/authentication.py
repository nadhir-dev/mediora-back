from typing import Literal, Dict
from uuid import uuid4
from secrets import token_hex, token_urlsafe
from random import randint
import hmac
from hashlib import sha256
from src.utils.validators import is_username, is_email
from src.utils.time import after
from fastapi import Request, HTTPException, status
from jose import jwt
from src.config.env import env
from src.schemas.users import UserInfo, UserInsertion, InsertUserOauth
from src.utils.validators import is_id


def format_data(data_in: UserInsertion, device_id: str):
    data = data_in.model_dump(exclude_none=True)

    info_fields = {"phone", "gender", "date_of_birth"}
    auth_fields = {"password"}

    user = {k: v for k, v in data.items() if k not in info_fields | auth_fields}
    info = {k: v for k, v in data.items() if k in info_fields}
    auth = {k: v for k, v in data.items() if k in auth_fields}

    session = {
        "refresh_token": gen_refresh_token(),
        "refresh_token_expires": after(days=60),
        "device_id": device_id,
    }

    user["id"] = info["id"] = auth["id"] = session["user_id"] = gen_id()

    user_data = UserInfo(user, auth, info, session)

    return user_data


def infer_identifier_type(identifier: str) -> Literal["username", "email"]:

    if is_username(identifier):
        return "username"
    elif is_email(identifier):
        return "email"
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid credential, should be valid email or username.",
        )


def get_token(
    request: Request,
    token_type: Literal["access", "refresh"] = "access",
    required: bool = False,
) -> str | None:

    header_token = request.headers.get("Authorization") or ""

    if header_token.startswith("Bearer "):
        return header_token.split(" ")[1]

    cookie_token = request.cookies.get(f"{token_type}_token", None)

    if required and not cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing {token_type} token."
        )

    return cookie_token


def gen_id():
    return uuid4()


def gen_refresh_token() -> str:
    return token_hex(16)


def gen_access_token(id) -> str:
    payload = {"id": str(id), "exp": after(minutes=15 * 100000)}

    return jwt.encode(payload, env.jwt_secret, algorithm="HS256")


def gen_random_code(length: int = 6) -> str:
    num = randint(10**length, 10 ** (length + 1) - 1)
    return str(num)


def gen_token():
    return token_urlsafe(16)


def hash_token(token: str) -> str:
    return hmac.new(env.hash_secret.encode(), token.encode(), sha256).hexdigest()


def get_device_id(
    request: Request, required: bool = False, generate: bool = False
) -> str | None:
    device_id = None

    if device_id_header := request.headers.get("X-Device-Id"):
        device_id = device_id_header
    elif device_id_cookie := request.cookies.get("device_id"):
        device_id = device_id_cookie

    if device_id and not is_id(device_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="invalid device id."
        )

    if not device_id and required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="missing device id."
        )

    if not device_id and generate:
        device_id = str(gen_id())

    return device_id


def get_creation_token(request: Request) -> str:
    creation_token = None

    if creation_token_header := request.headers.get("Creation-Token"):
        creation_token = creation_token_header
    elif creation_token_cookie := request.cookies.get("creation_token"):
        creation_token = creation_token_cookie

    if not creation_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="missing creation token."
        )

    return creation_token


def parse_google_provided_data(user_info: Dict[str, str]) -> InsertUserOauth:
    pass

    return InsertUserOauth(
        id=gen_id(),
        first_name=user_info.get("given_name", "user"),
        last_name=user_info.get("family_name", None),
        email=user_info["email"],
        google_open_id=user_info["sub"],
        username=f"username{randint(10**2,10**8)}",
        picture=user_info.get("picture", None),
    )
