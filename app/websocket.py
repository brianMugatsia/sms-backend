from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Optional
from app import auth
import logging
import json
import uuid

router = APIRouter()
logger = logging.getLogger("sms_backend")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_roles: Dict[WebSocket, str] = {}
        self.connection_ids: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()

        connection_id = str(uuid.uuid4())[:8]

        self.active_connections.append(websocket)
        self.connection_roles[websocket] = role
        self.connection_ids[websocket] = connection_id

        logger.info(
            "[WS %s] Connected role=%s total=%d",
            connection_id,
            role,
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket):
        connection_id = self.connection_ids.get(websocket, "unknown")

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        self.connection_roles.pop(websocket, None)
        self.connection_ids.pop(websocket, None)

        logger.info(
            "[WS %s] Disconnected total=%d",
            connection_id,
            len(self.active_connections),
        )

    async def broadcast(
        self,
        message: dict,
        role: Optional[str] = None,
    ):

        dead_connections = []

        logger.info(
            "Broadcasting to %d clients",
            len(self.active_connections),
        )

        for connection in list(self.active_connections):

            try:

                if (
                    role is None
                    or self.connection_roles.get(connection) == role
                ):
                    await connection.send_json(message)

            except Exception as e:

                logger.error("Broadcast failed: %s", e)

                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):

    if not token:

        await websocket.accept()

        await websocket.send_json(
            {
                "type": "error",
                "message": "Missing token",
            }
        )

        await websocket.close()

        return

    payload = auth.decode_access_token(token)

    if not payload:

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

    await manager.connect(websocket, role)

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

        logger.exception("WebSocket error: %s", e)

        manager.disconnect(websocket)