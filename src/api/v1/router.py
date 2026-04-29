from fastapi import APIRouter

from src.api.v1.endpoints.authentication import auth_router
from src.api.v1.endpoints.doctor_authentication import doctor_approvement_router
from src.api.v1.endpoints.users import users_router
from src.api.v1.endpoints.doctor_schedule import schedule_router
from src.api.v1.endpoints.appointments import appointments_router
from src.api.v1.endpoints.chat import chat_router
from src.api.v1.endpoints.feedback import feedback_router


router = APIRouter()

router.include_router(auth_router)
router.include_router(doctor_approvement_router)
router.include_router(users_router)
router.include_router(schedule_router)
router.include_router(appointments_router)
router.include_router(chat_router)
router.include_router(feedback_router, prefix="/doctors")
