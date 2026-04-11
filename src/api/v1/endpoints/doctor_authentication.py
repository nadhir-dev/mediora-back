from typing import Annotated

from starlette import status
from src.services.doctor_authentication import (
    fetch_my_request,
    saveRequest,
    fetch_doctors_requests,
    fetch_doctor_request,
    review_doctor_request,
)
from fastapi import APIRouter, Response, Depends, Body, Query
from src.schemas.users import SuccessMessage, User
from src.services.authentication import protect
from src.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.doctor_requests import DoctorRequest, DoctorRequests, RequestDocuments


doctor_approvement_router = APIRouter(prefix="/doctors-approvement")


@doctor_approvement_router.post("/request", response_model=SuccessMessage)
async def send_cerification_request(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    docs: Annotated[RequestDocuments, Body()],
    res: Response,
):
    await saveRequest(db=session, user=user, docs=docs)

    res.status_code = status.HTTP_201_CREATED
    return {"message": "request saved successfully."}


@doctor_approvement_router.get("/", response_model=DoctorRequests)
async def get_doctors_requests(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, lt=20, ge=1),
    page: int = Query(1, ge=1),
):
    requests = await fetch_doctors_requests(
        db=session, user=user, limit=limit, page=page
    )
    return {"data": requests}


@doctor_approvement_router.get("/mine", response_model=DoctorRequest)
async def get_my_request(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
):
    request = await fetch_my_request(db=session, user=user)

    return {"data": request}


@doctor_approvement_router.get("/{request_id}", response_model=DoctorRequest)
async def get_doctor_request(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    request_id: str,
):
    request = await fetch_doctor_request(db=session, user=user, request_id=request_id)

    return {"data": request}


@doctor_approvement_router.post("/{request_id}/approve", response_model=SuccessMessage)
async def approve_doctor_request(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request_id: str,
):
    await review_doctor_request(
        db=session, user=user, reaction="approve", request_id=request_id
    )

    return {"message": "request approved."}

    # check if user is admin
    # if that request is alrady validated or rejected throw an error
    # validate that request


@doctor_approvement_router.delete("/{request_id}/reject", response_model=SuccessMessage)
async def reject_doctor_request(
    user: Annotated[User, Depends(protect)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request_id: str,
):
    await review_doctor_request(
        db=session, user=user, reaction="reject", request_id=request_id
    )

    return {"message": "request rejected."}
    # check if user is admin
    # if that request is alrady validated or rejected throw an error
    # reject that request
