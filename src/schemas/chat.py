from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ChatResponses(str, Enum):
    message_sent = "message.sent"
    message_seen = "message.seen"
    # typing = "message.typing"
    connected = "ping"
    error = "error"


class ChatActions(str, Enum):
    send = "message.send"
    read = "message.read"
    typing = "message.typing"
    ping = "ping"


class Payload(BaseModel):
    conversation_id: UUID


class SendMessagePayload(Payload):
    message: str = Field(min_length=1)


class ReadMessagePayload(Payload):
    message_id: int = Field(ge=1)


class MessageSchema(BaseModel):
    type: ChatActions


class SendMessageSchema(MessageSchema):
    payload: SendMessagePayload


class ReadMessageSchema(MessageSchema):
    payload: ReadMessagePayload


class TypingMessageSchema(MessageSchema):
    payload: Payload


# SendMessage.model_validate(

# )
