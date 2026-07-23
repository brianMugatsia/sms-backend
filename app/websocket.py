import json
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter()

logger = logging.getLogger("sms_backend")


class ConnectionManager:

    def __init__(self):
        # Connections are now grouped by device_id instead of one flat list,
        # so a broadcast can be scoped to a single device's dashboard(s).
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        device_id: str,
    ):

        await websocket.accept()

        self.active_connections.setdefault(device_id, []).append(websocket)

        logger.info(
            "Dashboard connected. device_id=%s Total=%d",
            device_id,
            sum(len(conns) for conns in self.active_connections.values()),
        )

    def disconnect(
        self,
        websocket: WebSocket,
        device_id: str,
    ):

        conns = self.active_connections.get(device_id, [])
        if websocket in conns:
            conns.remove(websocket)

        # Clean up empty device buckets so the dict doesn't grow forever
        if device_id in self.active_connections and not self.active_connections[device_id]:
            del self.active_connections[device_id]

        logger.info(
            "Dashboard disconnected. device_id=%s Total=%d",
            device_id,
            sum(len(conns) for conns in self.active_connections.values()),
        )

    async def broadcast_to_device(
        self,
        device_id: str,
        message: dict,
    ):
        """
        Sends a message ONLY to dashboards connected under this specific
        device_id, instead of every connected client.
        """

        try:
            text = json.dumps(message, default=str)
        except Exception:
            logger.exception(
                "Failed to serialize broadcast payload: %r",
                message,
            )
            return

        dead_connections = []

        for connection in self.active_connections.get(device_id, []):

            try:

                await connection.send_text(text)

            except Exception:

                logger.exception(
                    "Failed to send to a dashboard connection; dropping it."
                )

                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection, device_id)


manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(
    websocket: WebSocket,
    device_id: str = Query(...),
):

    await manager.connect(websocket, device_id)

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

        manager.disconnect(websocket, device_id)

    except Exception as e:

        logger.exception(e)

        manager.disconnect(websocket, device_id)