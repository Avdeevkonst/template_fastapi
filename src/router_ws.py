import json
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_user_from_request
from src.crud import (
    create_message_model,
    delete_message_model,
    update_message_model,
)
from src.dependencies import get_async_session
from src.managers import manager
from src.models import User
from src.schemas import (
    CreateMessage,
    DeleteMessage,
    UpdateMessage,
    WSMessageRequest,
)

router = APIRouter()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <label>Token: <input type="text" id="token" autocomplete="off" value="some-key-token"/></label>
            <button onclick="connect(event)">Connect</button>
            <hr>
            <label>Message: <input type="text" id="messageText" autocomplete="off"/></label>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
        var ws = null;
            function connect(event) {
                var token = document.getElementById("token")
                ws = new WebSocket("ws://localhost:8000/oauth2/api/v1/ws?token=" + token.value);
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                event.preventDefault()
            }
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@router.get("/")
async def get():
    return HTMLResponse(html)


@router.websocket("/ws/{receiver}")
async def websocket_endpoint(
    *,
    websocket: WebSocket,
    user: Annotated[User, Depends(get_user_from_request)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    receiver: int,
):
    user_id = str(user.id)
    if not manager.is_connected(user_id):
        await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            validated_data = json.loads(data)
            message = WSMessageRequest.model_validate(validated_data)
            message.message.receiver_id = receiver
            if isinstance(message.message, CreateMessage):
                await create_message_model(db, message.message)
                await manager.send_message(message.message, websocket)
            elif isinstance(message.message, DeleteMessage):
                await delete_message_model(db, message.message)
            elif isinstance(message.message, UpdateMessage):
                await update_message_model(db, message.message)
                await manager.send_message(message.message, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
