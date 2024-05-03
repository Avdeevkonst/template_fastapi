from typing import Any

from fastapi import WebSocket

from src.schemas import CreateMessage, UpdateMessage


class Singleton:  # pragma: no cover
    def __new__(cls, *args: Any, **kwds: Any):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args: Any, **kwds: Any):
        pass


class WsConnectionManager(Singleton):
    def __init__(self):
        self.active_connections: dict[str, tuple[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, sender_id: str) -> None:
        await websocket.accept()
        self.active_connections[sender_id] = (websocket,)

    def disconnect(self, websocket: WebSocket, sender_id: str) -> None:
        if sender_id not in self.active_connections:
            return
        del self.active_connections[sender_id]

    async def send_message(
        self, message: CreateMessage | UpdateMessage, websocket: WebSocket
    ) -> None:
        if isinstance(message, CreateMessage):
            text = message.text or message.photo
        elif isinstance(message, UpdateMessage):
            text = message.text
        await websocket.send_text(text)  # pyright: ignore[reportArgumentType]

    def is_connected(self, user_id: str) -> bool:
        return bool(self.active_connections.get(user_id, False))


manager = WsConnectionManager()
