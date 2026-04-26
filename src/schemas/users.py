from typing import Annotated, Any, Optional, Self
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID
from enum import Enum
from datetime import date
from fastapi import HTTPException
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    StringConstraints,
    ConfigDict,
    model_validator,
)
from starlette import status


# from src.schemas.doctor_requests import ImageFile


Email = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", to_lower=True
    ),
]
Username = Annotated[
    str,
    StringConstraints(
        min_length=2, max_length=60, pattern=r"^[a-zA-Z0-9_]+$", to_lower=True
    ),
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=64)]
Phone = Annotated[
    str,
    StringConstraints(
        pattern=r"^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$", min_length=10
    ),
]


class Gender(str, Enum):
    male = "male"
    female = "female"


class ResetPassword(BaseModel):
    password: Password
    reset_token: str = Field(min_length=0)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if v[0].isspace() or v[-1].isspace():
            raise ValueError("Password cannot start or end with whitespace")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        if not any(not c.isalnum() and not c.isspace() for c in v):
            raise ValueError("Password must contain at least one special character")

        return v


class UserFlatResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: Optional[str] = None
    username: str
    email: str
    role: str
    is_active: bool
    is_doctor: bool
    specialty: Optional[str] = None
    joined_at: datetime
    picture: Optional[str] = None

    gender: Optional[str] = None
    date_of_birth: Optional[date]
    phone: Optional[str] = None
    clinic_posx: Optional[str] = None
    clinic_posy: Optional[str] = None
    degree: Optional[str] = None
    practice_start_date: Optional[date]
    description: Optional[str] = None
    institution: Optional[str] = None
    images_of_workplace: Optional[list[str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RegistrationRoles(str, Enum):
    user = "user"
    doctor = "doctor"


class Roles(str, Enum):
    user = "user"
    doctor = "doctor"
    admin = "admin"


class Speciality(str, Enum):
    general_practice = "general practice"
    family_medicine = "family medicine"
    internal_medicine = "internal medicine"
    pediatrics = "pediatrics"
    emergency_medicine = "emergency medicine"

    cardiology = "cardiology"
    dermatology = "dermatology"
    neurology = "neurology"
    psychiatry = "psychiatry"

    general_surgery = "general surgery"
    orthopedic_surgery = "orthopedic surgery"
    obstetrics_gynecology = "obstetrics and gynecology"

    ophthalmology = "ophthalmology"
    ent = "otolaryngology (ent)"

    radiology = "radiology"


class BaseUser(BaseModel):
    first_name: Name
    last_name: Optional[Name] = None
    username: Username
    email: Email


class UserPublic(BaseUser):
    id: UUID
    is_doctor: bool
    role: Roles
    specialty: Optional[Speciality] = None
    picture: Optional[str] = None


class User(UserPublic):
    is_active: bool
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    data: User


class ExtendedUserResponse(BaseModel):
    data: UserFlatResponse


class UpdateUser(BaseModel):
    first_name: Optional[Name] = None
    last_name: Optional[Name] = None
    username: Optional[Username] = None
    phone: Optional[Phone] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    description: Optional[str] = None
    # clinic_posx: Optional[float] = None
    # clinic_posy: Optional[float] = None
    clinic_posx: Optional[str] = None
    clinic_posy: Optional[str] = None

    # @field_serializer("clinic_posx", "clinic_posy")
    # def serialize_coords(self, value):
    #     return str(value)

    @model_validator(mode="after")
    def check_not_empty(self) -> Self:

        if all(field_value is None for field_value in self.model_dump().values()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "nothing to update.")

        if (self.clinic_posx and not self.clinic_posy) or (
            not self.clinic_posx and self.clinic_posy
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "please provide both x and y coordinates."
            )
        if self.clinic_posx and self.clinic_posy:

            try:
                float(self.clinic_posx)
                float(self.clinic_posy)
            except (TypeError, ValueError):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "invalid both x and y coordinates."
                )
        return self

    model_config = ConfigDict(extra="ignore")


class DoctorsResponse(BaseModel):
    data: list[BaseUser]


class UserInsertion(BaseUser):
    password: Password = Field(examples=["SecurePass123!"])
    role: RegistrationRoles = Field(examples=["doctor", "user"])
    phone: Optional[Phone] = Field(default=None, examples=["+1234567890"])
    gender: Optional[Gender] = Field(default=None, examples=["male", "female"])
    date_of_birth: Optional[date] = Field(default=None, examples=["1990-01-15"])
    specialty: Optional[Speciality] = None

    # device_id: str

    @model_validator(mode="after")
    def validate_user_data(self):

        if self.role == "doctor" and not self.specialty:
            raise ValueError("provide the spcecialty.")
        if self.role == "user" and self.specialty:
            raise ValueError("user has no specialty.")

        return self

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:

        if v[0].isspace() or v[-1].isspace():
            raise ValueError("Password cannot start or end with whitespace")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        if not any(not c.isalnum() and not c.isspace() for c in v):
            raise ValueError("Password must contain at least one special character")

        return v

    model_config = ConfigDict(extra="ignore")


class InsertUserOauth(BaseUser):
    id: UUID
    google_open_id: str
    picture: Optional[str] = None


# class User(BaseUser):
#     id: UUID
#     is_doctor: bool
#     role: Literal["user", "doctor", "admin"]

#     specialty: str | None
#     joined_at: datetime
#     is_active: bool = Field(exclude=True)
#     model_config = ConfigDict(from_attributes=True)


@dataclass
class UserInfo:
    """user -> auth -> info -> session"""

    user_table: dict[str, Any]
    auth_table: dict[str, Any]
    info_table: dict[str, Any]
    session_table: dict[str, Any]


class SigninCredentials(BaseModel):
    identifier: Username | Email
    password: Password


class SuccessMessage(BaseModel):
    message: str


class ExistsCheckResponse(BaseModel):
    exists: bool


class TokenWithMessage(BaseModel):
    message: str
    token: str = Field(examples=["34vrgwrVOaDJZhM4jbfk9g"])


class AccessToken(BaseModel):
    token: str = Field(
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjgzMDQ3Mjg4LTc2MDgtNGQyOC1iNmZiLWMwZjhhZjBmNGFkZCIsImV4cCI6MTg2MzkyNDQ5OX0.sXOuGp00d-EVGwMtazfD6uvLVegaKw7mh-Pv3UULVpA"
        ]
    )
    type: str = Field(examples=["Bearer"])


class DoctorListResponse(BaseModel):
    data: list[UserPublic]


class DoctorFlatResponse(UserFlatResponse):

    model_config = ConfigDict(from_attributes=True)
