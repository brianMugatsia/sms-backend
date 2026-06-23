from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List
from app import auth  # your JWT decode logic

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_roles: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_roles[websocket] = role

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_roles.pop(websocket, None)

    async def broadcast(self, message: dict, role: str | None = None):
        for connection in self.active_connections:
            if role is None or self.connection_roles.get(connection) == role:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/sms")
async def sms_websocket(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = auth.decode_access_token(token)
    except Exception as e:
        # invalid token format or signature
        await websocket.close(code=1008, reason="Invalid token")
        return

    if payload is None:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    role = payload.get("role", "user")

    await manager.connect(websocket, role)
    try:
        while True:
            # keep-alive ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
