from uuid import UUID

from jose import JWTError, jwt

from src.config.env import env


def get_user_id(token: str) -> UUID | None:
    try:
        decoded = jwt.decode(token, env.jwt_secret, algorithms=["HS256"])
        return UUID(decoded["id"])
    except (JWTError, KeyError, ValueError) as err:

        return None
