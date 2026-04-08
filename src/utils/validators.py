from typing import Any
from pydantic import TypeAdapter,UUID4
from src.schemas.users import Username, Password, Phone, Email


def get_type(name: str):
    match name:
        case "username":
            return Username
        case "password":
            return Password
        case "email":
            return Email
        case "phone":
            return Phone
        case "uuid":
            return UUID4
        case _:
            raise Exception("unknown validation option in src.utils.validators.")


def validate(adaptor):
    v = TypeAdapter(adaptor)

    def _(value: Any):
        try:
            v.validate_python(value)
        except Exception:
            return False
        else:
            return True

    return _


is_email = validate(get_type("email"))
is_phone = validate(get_type("phone"))
is_username = validate(get_type("username"))
is_password = validate(get_type("password"))
is_id = validate(get_type("uuid"))