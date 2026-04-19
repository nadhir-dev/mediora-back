from datetime import date, timedelta, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class MakeAppointment(BaseModel):

    # doctor_id: UUID
    service_id: UUID
    date: date

    @field_validator("date")
    @classmethod
    def field(cls, v):
        date_after_week = date.today() + timedelta(days=7)

        if v >= date_after_week:
            raise ValueError("you cannot make appointments after 7 days from now.")

        if v <= date.today():
            raise ValueError("you cannot make appointments for today or earlier.")

        return v


class UserResponseForAppointment(BaseModel):
    first_name: str
    last_name: str
    username: str
    is_doctor: bool
    specialty: Optional[str] = None
    joined_at: datetime
    picture: Optional[str] = None


class Appointment(BaseModel):
    id: UUID
    service_id: UUID
    token: str
    created_at: datetime
    doctor_id: UUID
    patient_id: UUID
    date: date
    status: AppointmentStatus


class AppointmentWithUsersPopulated(Appointment):
    doctor: UserResponseForAppointment
    patient: UserResponseForAppointment


class AppointmentResponse(BaseModel):
    data: Appointment
    model_config = ConfigDict(from_attributes=True)


class ExtendedAppointmentResponse(BaseModel):
    data: AppointmentWithUsersPopulated
    model_config = ConfigDict(from_attributes=True)


class AppointmentWithDoctorPopulated(BaseModel):
    id: UUID
    service_id: UUID
    token: str
    created_at: datetime
    doctor_id: UUID
    patient_id: UUID
    date: date
    status: str

    doctor: UserResponseForAppointment


class AppointmentWithPatientPopulated(BaseModel):
    id: UUID
    service_id: UUID
    token: str
    created_at: datetime
    doctor_id: UUID
    patient_id: UUID
    date: date

    status: str

    patient: UserResponseForAppointment


class DoctorAppointmentsResponse(BaseModel):
    data: list[AppointmentWithPatientPopulated]
    model_config = ConfigDict(from_attributes=True)


class PatientAppointmentsResponse(BaseModel):
    data: list[AppointmentWithDoctorPopulated]
    model_config = ConfigDict(from_attributes=True)


class CheckoutUrl(BaseModel):
    url: str


class CheckoutUrlResponse(BaseModel):
    data: CheckoutUrl
    model_config = ConfigDict(from_attributes=True)


# {
#   "id": "01hjjjzf7wbc454te45mwx35fe",
#   "entity": "event",
#   "livemode": "false",
#   "type": "checkout.paid",
#   "data": {
#     "id": "01hjjj9aymmrwe664nbzrv84sg",
#     "entity": "checkout",
#     "fees": 1250,
#     "amount": 50000,
#     "locale": "ar",
#     "status": "paid",
#     "metadata": null,
#     "created_at": 1703577693,
#     "invoice_id": null,
#     "updated_at": 1703578418,
#     "customer_id": "01hjjjzf07chnbkcjax2vs58fv",
#     "description": null,
#     "failure_url": null,
#     "success_url": "https://your-cool-website.com/payments/success",
#     "payment_method": null,
#     "payment_link_id": null,
#     "pass_fees_to_customer": null,
#     "chargily_pay_fees_allocation": "customer",
#     "shipping_address": null,
#     "collect_shipping_address": 1,
#     "discount": null,
#     "amount_without_discount": null,
#     "url": "https://pay.chargily.dz/test/checkouts/01hjjj9aymmrwe664nbzrv84sg/pay"
#   },
#   "created_at": 1703578418,
#   "updated_at": 1703578418
# }
