import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast_to_session(self, session_id: str, data: dict) -> None:
        if session_id not in self._connections:
            return
        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in self._connections[session_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[session_id].discard(ws)

    def has_connections(self, session_id: str) -> bool:
        return session_id in self._connections and len(self._connections[session_id]) > 0


ws_manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)
    try:
        from main import simulation_manager
        sim = simulation_manager.get_session(session_id)
        if sim:
            snapshot = sim.get_snapshot()
            await websocket.send_text(json.dumps({
                "type": "state_snapshot",
                "data": {
                    "tick": snapshot.tick,
                    "clock_mode": snapshot.clock_mode,
                    "speed": snapshot.speed,
                    "nodes": [vars(n) for n in snapshot.nodes],
                    "in_flight_messages": snapshot.in_flight_messages,
                    "partitions": snapshot.partitions,
                    "events_recent": snapshot.events_recent,
                },
            }))

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, session_id)
