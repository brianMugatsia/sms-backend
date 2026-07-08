import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

logger = logging.getLogger("sms_backend")


class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(
        self,
        websocket: WebSocket,
    ):

        await websocket.accept()

        self.active_connections.append(websocket)

        logger.info(
            "Dashboard connected. Total=%d",
            len(self.active_connections),
        )

    def disconnect(
        self,
        websocket: WebSocket,
    ):

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        logger.info(
            "Dashboard disconnected. Total=%d",
            len(self.active_connections),
        )

    async def broadcast(
        self,
        message: dict,
    ):

        dead_connections = []

        for connection in self.active_connections:

            try:

                await connection.send_json(message)

            except Exception:

                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(
    websocket: WebSocket,
):

    await manager.connect(websocket)

    try:

        while True:

            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except Exception:
                message = {}

            # Heartbeat
            if message.get("type") == "ping":

                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )

                continue

            # Optional future commands
            if message.get("type") == "stats":

                await websocket.send_json(
                    {
                        "type": "stats",
                        "message": "Not implemented",
                    }
                )

                continue

            # Echo (for testing)
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