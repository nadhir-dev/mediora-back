from collections import defaultdict
from typing import Sequence
from uuid import UUID

from fastapi import WebSocket


class ChatManager:
    def __init__(self):
        self.active_connections: dict[UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, ws: WebSocket, user_id: UUID):

        self.active_connections[user_id].append(ws)

    async def send_to_one(self, user_id: UUID, message):

        for connection in self.active_connections[user_id]:
            await connection.send_json(message)

    async def send_to_many(self, user_ids: Sequence[UUID], message):

        for user_id in user_ids:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    def disconnect(self, ws: WebSocket, user_id: UUID):
        connections = self.active_connections[user_id]

        if ws in connections:
            connections.remove(ws)

        if not connections and user_id in self.active_connections:
            del self.active_connections[user_id]
