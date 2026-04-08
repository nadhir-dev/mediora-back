from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket
from pydantic import ValidationError
from starlette import status
from json import loads
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.connection import get_db
from src.schemas.chat import (
    ChatActions,
    ChatResponses,
    ReadMessageSchema,
    SendMessageSchema,
    TypingMessageSchema,
)
from src.schemas.users import User
from src.services.authentication import protect
from src.services.messaging import (
    create_message,
    get_other_participant_ids,
    get_recent_contacts,
    get_recent_messages,
    read_message,
)
from src.utils.chat_manager import ChatManager
from src.utils.messaging import get_user_id


chat_router = APIRouter(prefix="/chat")

manager = ChatManager()


@chat_router.get("/contacts/latest")
async def get_contacts_with_latest_messages(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    limit: int = Query(10),
    page: int = Query(1),
):
    output = await get_recent_contacts(db_session=db, user=user, limit=limit, page=page)
    return output


@chat_router.get("/conversations/:{id}/messages")
async def get_messages(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(protect)],
    id: UUID,
    limit: int = Query(10),
    page: int = Query(1),
):
    output = await get_recent_messages(
        db_session=db, user=user, conversation_id=id, limit=limit, page=page
    )
    return output


@chat_router.websocket("/ws")
async def f(ws: WebSocket):
    await ws.accept()

    token = ws.query_params.get("token")
    if token is None:
        await ws.close(status.WS_1008_POLICY_VIOLATION)
        return

    if (user_id := get_user_id(token)) is None:
        await ws.send_json({"message": "error"})
        return

    await manager.connect(ws, user_id)

    while True:
        try:
            recieved = await ws.receive_json()

            match recieved.get("type", None):

                case ChatActions.send.value:

                    sendMessageInput = SendMessageSchema.model_validate(recieved)
                    message, members = await create_message(
                        user_id=user_id,
                        conversation_id=sendMessageInput.payload.conversation_id,
                        message_str=sendMessageInput.payload.message,
                    )

                    await manager.send_to_many(
                        members,
                        (
                            {
                                "type": ChatResponses.message_sent,
                                "payload": message,
                            }
                        ),
                    )

                case ChatActions.read.value:

                    readMessageInput = ReadMessageSchema.model_validate(recieved)

                    participants_ids, info = await read_message(
                        user_id=user_id,
                        message_id=readMessageInput.payload.message_id,
                        conversation_id=readMessageInput.payload.conversation_id,
                    )

                    await manager.send_to_many(
                        participants_ids,
                        {
                            "type": ChatResponses.message_seen,
                            "payload": info,
                        },
                    )

                case ChatActions.typing.value:

                    typingMessageInput = TypingMessageSchema.model_validate(recieved)

                    participants_ids = await get_other_participant_ids(
                        user_id, typingMessageInput.payload.conversation_id
                    )

                    await manager.send_to_many(
                        participants_ids,
                        {
                            "type": "message.typing",
                            "payload": {"user_id": str(user_id)},
                        },
                    )

                case ChatActions.ping.value:
                    await manager.send_to_one(
                        user_id, {"type": ChatResponses.connected, "payload": "pong"}
                    )

                case _:
                    raise ValueError(
                        "unknown type, should be message.send, message.read, message.typing, ping).",
                    )

        except ValidationError as e:
            await ws.send_json(
                {
                    "type": ChatResponses.error,
                    "payload": {
                        "reason": "validation",
                        "structure": "json",
                        "value": loads(e.json(include_url=False)),
                    },
                }
            )

        except ValueError as e:
            await ws.send_json(
                {
                    "type": ChatResponses.error,
                    "payload": {
                        "reason": "logic",
                        "structure": "text",
                        "value": str(e),
                    },
                }
            )

        except Exception as e:
            await ws.send_json(
                {
                    "type": ChatResponses.error,
                    "payload": {
                        "reason": "unknown",
                        "structure": "text",
                        "value": "something went wrong.",
                    },
                }
            )


# m = {"type": "message.read/message.send/ping/message.typing", "payload": "str"}
# send payload ={ conversation_id}
# read payload ={ conversation_id}
