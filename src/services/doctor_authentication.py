from typing import Literal
from fastapi import HTTPException, status
from sqlalchemy import select, exists, update
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError

# from src.models.appointments import DoctorWallet
from src.schemas.users import User
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.time import now

from src.schemas.doctor_requests import RequestDocuments
from src.utils.authentication import gen_id
from src.models.doctor_authentication import DoctorRequest, RequestMedia, Media
from src.models.users import Users


async def saveRequest(*, db: AsyncSession, user: User, docs: RequestDocuments):

    if user.role != "doctor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only doctors are allowed.")

    if user.is_doctor:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "you're already certified doctor."
        )

    user_id = user.id
    exists_stmt = select(
        exists(DoctorRequest).where(
            DoctorRequest.user_id == user_id, DoctorRequest.reviewed == False
        )
    )
    any_unreviewied_requests = await db.scalar(exists_stmt)

    if any_unreviewied_requests:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "you're precedent request hasn't been reviewed yet.",
        )
    # optional: check if assests exist in db, cloud
    # result = await run_in_threadpool(check_resources,...args)

    request_id = gen_id()
    request = DoctorRequest(
        id=request_id, user_id=user_id, wallet_password=docs.wallet_password
    )
    del docs.wallet_password
    media = []
    request_media = []
    try:
        for k, v in docs.model_dump().items():
            if k == "images_of_workplace":
                for value in v:

                    media_id = gen_id()
                    media.append(
                        Media(
                            id=media_id,
                            public_id=value["public_id"],
                            url=value["secure_url"],
                            resource_type=value["public_id"],
                            format=value["format"],
                        )
                    )

                    request_media.append(
                        RequestMedia(
                            id=gen_id(),
                            document_type="images_of_workplace",
                            request_id=request_id,
                            document_id=media_id,
                        )
                    )
            else:
                media_id = gen_id()

                media.append(
                    Media(
                        id=media_id,
                        public_id=v["public_id"],
                        url=v["secure_url"],
                        resource_type=v["resource_type"],
                        format=v["format"],
                    )
                )

                request_media.append(
                    RequestMedia(
                        id=gen_id(),
                        document_type=k,
                        request_id=request_id,
                        document_id=media_id,
                    )
                )
        db.add_all([request, *media, *request_media])
        await db.commit()

    except IntegrityError as e:
        await db.rollback()
        err_msg = str(e.orig)

        if "unique_public_id_per_resource_type" in err_msg:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "data provided is contradictory, this document public id and resource type already exists.",
            )

        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "data provided is contradictory, most likely the documents you provided are not correct.",
        )


async def fetch_my_request(*, db: AsyncSession, user: User):

    if user.role != "doctor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only doctors are allowed.")

    stmt = (
        select(DoctorRequest)
        .where(DoctorRequest.user_id == user.id)
        .options(
            selectinload(DoctorRequest.request_media).selectinload(RequestMedia.media)
        )
    )

    request = (await db.scalars(stmt)).one_or_none()

    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found.")

    return request


async def fetch_doctors_requests(
    *, db: AsyncSession, user: User, limit: int, page: int
):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden.")

    stmt = (
        select(DoctorRequest)
        .where(DoctorRequest.reviewed == False)
        .limit(limit)
        .offset((page - 1) * limit)
        .options(
            joinedload(DoctorRequest.user).load_only(
                Users.id,
                Users.first_name,
                Users.last_name,
                Users.email,
                Users.picture,
            )
        )
    )
    requests = (await db.scalars(stmt)).all()

    return requests


async def fetch_doctor_request(*, db: AsyncSession, user: User, request_id: str):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden.")
    stmt = (
        select(DoctorRequest)
        .where(DoctorRequest.id == request_id)
        .options(
            selectinload(DoctorRequest.request_media).selectinload(RequestMedia.media)
        )
    )

    request = (await db.scalars(stmt)).one_or_none()

    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found.")

    return request


async def review_doctor_request(
    *,
    db: AsyncSession,
    reaction: Literal["approve", "reject"],
    user: User,
    request_id: str,
):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden.")

    stmt = (
        update(DoctorRequest)
        .values(reviewed=True, reviewed_at=now())
        .where(DoctorRequest.id == request_id, DoctorRequest.reviewed == False)
        .returning(DoctorRequest.user_id, DoctorRequest.wallet_password)
    )

    data = await db.scalar(stmt)

    if not data:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "request not found or has already been reviewed."
        )

    if reaction == "approve":
        pass
        # wallet = DoctorWallet(doctor_id=data.user_id, password=data.wallet_password)
        # approve_doctor_stmt = (
        #     update(Users).values(is_doctor=True).where(Users.id == data)
        # )
        # db_session.add(wallet)
        # await db_session.execute(approve_doctor_stmt)

    await db.commit()
