from datetime import datetime
from uuid import UUID
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.users import Email, Password


class PDF(BaseModel):
    public_id: str
    format: Literal["pdf"]
    resource_type: Literal["raw"]

    model_config = ConfigDict(from_attributes=True)


class ImageFile(BaseModel):
    public_id: str
    format: Literal["jpg", "jpeg", "png", "webp"]
    resource_type: Literal["image"]

    model_config = ConfigDict(from_attributes=True)


class RequestDocuments(BaseModel):
    degree: ImageFile
    employment_certificate: ImageFile
    images_of_workplace: List[ImageFile]
    commercial_registration_certificate: ImageFile
    wallet_password: Password

    model_config = ConfigDict(from_attributes=True)


class DoctorRequesting(BaseModel):
    id: UUID
    first_name: str
    last_name: Optional[str] = None
    email: Email
    picture: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BaseRequest(BaseModel):
    id: UUID
    created_at: datetime
    user: DoctorRequesting

    model_config = ConfigDict(from_attributes=True)


class DoctorRequests(BaseModel):
    data: list[BaseRequest]

    model_config = ConfigDict(from_attributes=True)


class Media(BaseModel):
    id: UUID
    # url: str
    public_id: str
    resource_type: str
    format: str


class RequestMedia(BaseModel):
    id: UUID
    document_type: str

    request_id: UUID
    document_id: UUID

    media: Media


class ExtendedRequest(BaseModel):
    id: UUID
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed: bool
    request_media: list[RequestMedia]

    model_config = ConfigDict(from_attributes=True)


class DoctorRequest(BaseModel):
    data: ExtendedRequest
