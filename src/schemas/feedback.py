from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.schemas.users import UserPublic


class FeedBack(BaseModel):
    id: UUID
    body: str
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime
    patient: UserPublic


class FeedBackWithoutPatient(BaseModel):
    id: UUID
    body: str
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime


class FeedBacksResponse(BaseModel):
    data: list[FeedBack]
    model_config = ConfigDict(from_attributes=True)


class FeedBackResponse(BaseModel):
    data: FeedBack
    model_config = ConfigDict(from_attributes=True)


class FeedBackWithoutPatientResponse(BaseModel):
    data: FeedBackWithoutPatient
    model_config = ConfigDict(from_attributes=True)
