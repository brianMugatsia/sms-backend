import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app import auth

router = APIRouter()

logger = logging.getLogger("sms_backend")


class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_roles: Dict[WebSocket, str] = {}

    async def connect(
        self,
        websocket: WebSocket,
        role: str,
    ):

        await websocket.accept()

        self.active_connections.append(websocket)

        self.connection_roles[websocket] = role

        logger.info(
            "WebSocket connected (%s). Total=%d",
            role,
            len(self.active_connections),
        )

    def disconnect(
        self,
        websocket: WebSocket,
    ):

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        self.connection_roles.pop(
            websocket,
            None,
        )

        logger.info(
            "WebSocket disconnected. Total=%d",
            len(self.active_connections),
        )

    async def broadcast(
        self,
        message: dict,
        role: Optional[str] = None,
    ):

        dead_connections = []

        for connection in self.active_connections:

            try:

                if (
                    role is None
                    or self.connection_roles.get(connection)
                    == role
                ):

                    await connection.send_json(message)

            except Exception:

                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):

    if token is None:

        await websocket.accept()

        await websocket.send_json(
            {
                "type": "error",
                "message": "Missing token",
            }
        )

        await websocket.close()

        return

    payload = auth.decode_token(token)

    if payload is None:

        await websocket.accept()

        await websocket.send_json(
            {
                "type": "error",
                "message": "Invalid token",
            }
        )

        await websocket.close()

        return

    role = payload.get("role", "user")

    await manager.connect(
        websocket,
        role,
    )

    try:

        while True:

            data = await websocket.receive_text()

            try:

                message = json.loads(data)

            except Exception:

                message = {
                    "type": "raw",
                    "data": data,
                }

            if message.get("type") == "ping":

                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )

                continue

            await websocket.send_json(
                {
                    "type": "echo",
                    "payload": message,
                }
            )

    except WebSocketDisconnect:

        manager.disconnect(websocket)

    except Exception as e:

        logger.exception(e)

        manager.disconnect(websocket)