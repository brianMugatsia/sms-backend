import json
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter()
logger = logging.getLogger("sms_backend")


class ConnectionManager:
    def __init__(self):
        # Keyed by device_id: Dict[str, List[WebSocket]]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_connections.setdefault(device_id, []).append(websocket)

        logger.info(
            "Dashboard connected | device_id=%s | active_device_connections=%d | total_connections=%d",
            device_id,
            len(self.active_connections[device_id]),
            sum(len(conns) for conns in self.active_connections.values()),
        )

    def disconnect(self, websocket: WebSocket, device_id: str):
        conns = self.active_connections.get(device_id, [])
        if websocket in conns:
            conns.remove(websocket)

        # Clean up empty device buckets
        if device_id in self.active_connections and not self.active_connections[device_id]:
            del self.active_connections[device_id]

        logger.info(
            "Dashboard disconnected | device_id=%s | total_connections=%d",
            device_id,
            sum(len(conns) for conns in self.active_connections.values()),
        )

    async def broadcast_to_device(self, device_id: str, message: dict):
        """
        Sends payload exclusively to sockets attached to the specified device_id.
        """
        conns = self.active_connections.get(device_id, [])
        if not conns:
            return

        try:
            text = json.dumps(message, default=str)
        except Exception:
            logger.exception("Failed to serialize broadcast payload: %r", message)
            return

        dead_connections: List[WebSocket] = []

        # Iterate over a shallow copy to prevent mutation issues during disconnects
        for connection in list(conns):
            try:
                await connection.send_text(text)
            except Exception:
                logger.warning(
                    "Failed to push WS message to client | device_id=%s. Marking dead.",
                    device_id,
                )
                dead_connections.append(connection)

        # Remove stale sockets
        for connection in dead_connections:
            self.disconnect(connection, device_id)


manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(
    websocket: WebSocket,
    device_id: str = Query(..., min_length=1),
):
    await manager.connect(websocket, device_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except Exception:
                message = {}

            msg_type = message.get("type")

            # Heartbeat ping/pong
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Diagnostic Echo
            await websocket.send_json(
                {
                    "type": "echo",
                    "payload": message,
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected gracefully | device_id=%s", device_id)
    except Exception as e:
        logger.error("WebSocket disconnected with error | device_id=%s | error=%s", device_id, str(e))
    finally:
        # Guarantees resource cleanup regardless of how loop terminates
        manager.disconnect(websocket, device_id)