from datetime import date, timedelta
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator


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
