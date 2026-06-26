from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Dict, Optional
from app import auth
import logging
import json

router = APIRouter()
logger = logging.getLogger("sms_backend")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_roles: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, role: str):
        #  no websocket.accept() here
        self.active_connections.append(websocket)
        self.connection_roles[websocket] = role

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_roles.pop(websocket, None)

    async def broadcast(self, message: dict, role: Optional[str] = None):
        for connection in list(self.active_connections):
            try:
                if role is None or self.connection_roles.get(connection) == role:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")


#  Define manager at module level so other files can import it
manager = ConnectionManager()


@router.websocket("/ws/sms")
async def sms_websocket(websocket: WebSocket, token: Optional[str] = Query(None)):
    #  Accept here only once
    await websocket.accept()
    print("WS CONNECT ATTEMPT")
    print("TOKEN:", token)

    if not token:
        await websocket.send_json({"type": "error", "message": "Missing token"})
        await websocket.close()
        return

    try:
        payload = auth.decode_access_token(token)
        print("JWT:", payload)
        if not payload:
            raise Exception("Invalid token")
    except Exception as e:
        print("AUTH ERROR:", str(e))
        await websocket.send_json({"type": "error", "message": "Invalid token"})
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
                message = {"type": "raw", "data": data}

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json({"type": "echo", "payload": message})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
