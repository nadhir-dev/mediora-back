from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4


from sqlalchemy import TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.connection import BASE
from src.utils.time import now

if TYPE_CHECKING:
    from users import Users


class Messages(BASE):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    body: Mapped[str] = mapped_column()
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="cascade")
    )
    created_at: Mapped[datetime] = mapped_column(default=now, type_=TIMESTAMP(True))


class Conversations(BASE):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(nullable=True)
    is_group: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now, type_=TIMESTAMP(True))

    members: Mapped["ConversationMembers"] = relationship(
        "ConversationMembers",
        uselist=True,
        foreign_keys="[ConversationMembers.conversation_id]",
    )


class ConversationMembers(BASE):
    __tablename__ = "conversation_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    last_message_seen_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("messages.id", ondelete="cascade"), nullable=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="cascade")
    )
    joined_at: Mapped[datetime] = mapped_column(default=now, type_=TIMESTAMP(True))

    user: Mapped["Users"] = relationship("Users", foreign_keys=user_id)
