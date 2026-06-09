import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.db import init_db
from engine.cluster import SimulationCluster, ClusterConfig
from api.websocket import ws_manager


class SimulationManager:
    """Manages active simulation sessions and their play loops."""

    def __init__(self) -> None:
        self._sessions: dict[str, SimulationCluster] = {}
        self._play_tasks: dict[str, asyncio.Task] = {}

    def create_session(self, session_id: str, config: ClusterConfig) -> SimulationCluster:
        if session_id in self._sessions:
            self.remove_session(session_id)
        cluster = SimulationCluster(config)
        self._sessions[session_id] = cluster
        return cluster

    def get_session(self, session_id: str) -> SimulationCluster | None:
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        self.stop_play_loop(session_id)
        self._sessions.pop(session_id, None)

    def start_play_loop(self, session_id: str) -> None:
        self.stop_play_loop(session_id)
        task = asyncio.create_task(self._play_loop(session_id))
        self._play_tasks[session_id] = task

    def stop_play_loop(self, session_id: str) -> None:
        task = self._play_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

    async def _play_loop(self, session_id: str) -> None:
        from engine.clock import ClockMode

        sim = self._sessions.get(session_id)
        if not sim:
            return

        try:
            while sim.clock.mode == ClockMode.PLAYING:
                sim.step()
                await self.broadcast(session_id)
                sleep_time = 1.0 / (1000.0 * sim.clock.speed)
                sleep_time = max(0.001, min(0.1, sleep_time))
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass

    async def broadcast(self, session_id: str) -> None:
        sim = self._sessions.get(session_id)
        if not sim:
            return
        if not ws_manager.has_connections(session_id):
            return

        snapshot = sim.get_snapshot()
        await ws_manager.broadcast_to_session(session_id, {
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
        })


simulation_manager = SimulationManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    for session_id in list(simulation_manager._play_tasks.keys()):
        simulation_manager.stop_play_loop(session_id)


app = FastAPI(title="Raft Simulation Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import sessions_router, simulation_router, cluster_router, websocket_router

app.include_router(sessions_router)
app.include_router(simulation_router)
app.include_router(cluster_router)
app.include_router(websocket_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
