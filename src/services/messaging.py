from typing import Sequence
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from src.db.connection import async_session
from src.models.messaging import ConversationMembers, Conversations, Messages
from src.models.users import Users
from src.schemas.chat import ChatUpdates
from src.schemas.users import User


async def create_message(
    user_id: UUID, conversation_id: UUID, message_str: str
) -> tuple[dict[str, str | int], list[UUID]]:

    async with async_session() as db:

        stmt = select(ConversationMembers.user_id).where(
            ConversationMembers.conversation_id == conversation_id,
        )

        conversation_members = (await db.scalars(stmt)).all()

        if not conversation_members:
            raise ValueError("conversation with this id doesn't exist.")
        if user_id not in conversation_members:
            raise ValueError("conversation with this id doesn't include you.")

        message = Messages(
            sender_id=user_id, body=message_str, conversation_id=conversation_id
        )

        db.add(message)

        conversation_members = [member_id for member_id in conversation_members]

        await db.commit()

        return {
            "message_id": message.id,
            "body": message.body,
            "sender_id": str(message.sender_id),
            "conversation_id": str(message.conversation_id),
            "created_at": str(message.created_at),
        }, conversation_members


async def get_other_participant_ids(
    user_id: UUID, conversation_id: UUID
) -> Sequence[UUID]:
    async with async_session() as db:

        stmt = select(ConversationMembers.user_id).where(
            ConversationMembers.conversation_id == conversation_id,
        )

        participant_ids = (await db.scalars(stmt)).all()

        if not participant_ids:
            raise ValueError("conversation with this id doesn't exist.")
        if user_id not in participant_ids:
            raise ValueError("conversation with this id doesn't include you.")

        participant_ids = [
            member_id for member_id in participant_ids if member_id != user_id
        ]

        await db.commit()
        return participant_ids


async def read_message(
    user_id: UUID, message_id: int, conversation_id: UUID
) -> tuple[Sequence[UUID], dict[str, str]]:
    async with async_session() as db:

        stmt = select(ConversationMembers).where(
            ConversationMembers.conversation_id == conversation_id,
        )

        memberships = (await db.scalars(stmt)).all()

        if not memberships:
            raise ValueError(f"no conversations matching the id {conversation_id}.")

        for v in memberships:
            if v.user_id == user_id:
                membership = v
                break

        if (
            membership.last_message_seen_id is not None
            and membership.last_message_seen_id > message_id
        ):
            raise ValueError(
                f"cannot set message with id {message_id} as the last seen message, it came after the current one with id {membership.last_message_seen_id}."
            )

        if (
            membership.last_message_seen_id is not None
            and membership.last_message_seen_id == message_id
        ):
            raise ValueError(
                f"message with id {message_id} is already the last seen message."
            )

        try:
            membership.last_message_seen_id = message_id
            await db.commit()

        except IntegrityError:
            raise ValueError(f"message with id {message_id} doesn't exist?")

        else:

            participants_ids = [membership.user_id for membership in memberships]
            return participants_ids, {
                "message_id": str(message_id),
                "user_id": str(user_id),
            }


async def get_recent_contacts(*, db: AsyncSession, user: User, limit: int, page: int):

    subquery = (
        select(Messages.conversation_id, func.max(Messages.created_at).label("latest"))
        .group_by(Messages.conversation_id)
        .subquery()
    )

    stmt = (
        select(
            Conversations,
            Users.id,
            Users.first_name,
            Users.last_name,
            Users.username,
            Users.picture,
            Messages.body,
        )
        .select_from(Conversations)
        .join(
            ConversationMembers, ConversationMembers.conversation_id == Conversations.id
        )
        .join(Users, Users.id == ConversationMembers.user_id)
        .outerjoin(subquery, subquery.c.conversation_id == Conversations.id)
        .outerjoin(
            Messages,
            (Messages.conversation_id == Conversations.id)
            & (Messages.created_at == subquery.c.latest),
        )
        .where(
            (ConversationMembers.user_id == user.id)
            & (
                Conversations.id.in_(
                    select(ConversationMembers.conversation_id).where(
                        ConversationMembers.user_id == user.id
                    )
                )
            )
        )
        .limit(limit)
        .offset((page - 1) * limit)
    )

    data = (await db.execute(stmt)).all()
    output = []

    for v in data:
        (
            conversation,
            user_id,
            first_name,
            last_name,
            username,
            picture,
            last_message,
        ) = v

        # if we upgrade chat to be more than 1-1 we need to modify the formatting here
        output.append(
            {
                "id": conversation.id,
                "name": conversation.name,
                "is_group": conversation.is_group,
                "last_message": last_message,
                "created_at": conversation.created_at,
                "user": {
                    "id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "picture": picture,
                },
            }
        )

    return output


async def get_recent_messages(
    *, db: AsyncSession, user: User, conversation_id: UUID, limit: int, page: int
):
    exists_stmt = select(
        exists(Conversations)
        .where(Conversations.id == conversation_id)
        .label("conversation_exists"),
        exists()
        .where(
            ConversationMembers.conversation_id == conversation_id,
            ConversationMembers.user_id == user.id,
        )
        .label("conversations_includes_user"),
    )

    data = (await db.execute(exists_stmt)).one()

    if not data.conversation_exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "this conversation doesn't exists."
        )
    if not data.conversations_includes_user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "this conversation doesn't include you."
        )

    stmt = (
        select(Messages)
        .where(
            Messages.conversation_id == conversation_id,
        )
        .limit(limit)
        .offset((page - 1) * limit)
    )

    data = (await db.scalars(stmt)).all()

    return data


async def update_chat(
    *, db: AsyncSession, user: User, conversation_id: UUID, updates: ChatUpdates
):

    subquery = select(
        exists().where(
            ConversationMembers.conversation_id == conversation_id,
            ConversationMembers.user_id == user.id,
        )
    ).scalar_subquery()

    stmt = select(Conversations, subquery.label("user_is_member")).where(
        ConversationMembers.conversation_id == conversation_id,
    )

    data = (await db.execute(stmt)).one_or_none()

    if data is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "there is no conversations matching this id."
        )

    conversation, user_is_member = data

    if not user_is_member:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "you're not a member of this chat."
        )
    conversation.name = updates.name
    await db.commit()
    return conversation

    # stmt = select(
    #     exists().where(
    #         ConversationMembers.conversation_id == conversation_id,
    #         ConversationMembers.user_id == user.id,
    #     )
    # )

    # user_is_member = await db.scalar(stmt)

    # if not user_is_member:
    #     raise HTTPException(
    #         status.HTTP_403_FORBIDDEN, "you're not a member of this chat or it doesn't include you."
    #     )
    # updates_dict = updates.model_dump()
    # stmt = (
    #     update(Conversations)
    #     .values(**updates_dict)
    #     .where(Conversations.id == conversation_id)
    #     .returning(Conversations)
    # )

    # conversation =(await db.scalars(stmt)).one()
    # return conversation
