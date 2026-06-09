from fastapi import APIRouter, HTTPException

from models.schemas import StepRequest, SpeedRequest

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["simulation"])


def _get_sim(session_id: str):
    from main import simulation_manager
    sim = simulation_manager.get_session(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found. Call /start first.")
    return sim


@router.post("/start")
async def start_simulation(session_id: str):
    from main import simulation_manager
    from models.db import get_db
    from models.schemas import ClusterConfigSchema
    from engine.cluster import ClusterConfig

    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    config_schema = ClusterConfigSchema.model_validate_json(row["config_json"])
    config = ClusterConfig(
        node_count=config_schema.node_count,
        base_delay=config_schema.base_delay,
        delay_jitter=config_schema.delay_jitter,
        packet_loss_rate=config_schema.packet_loss_rate,
        election_timeout_min=config_schema.election_timeout_min,
        election_timeout_max=config_schema.election_timeout_max,
        heartbeat_interval=config_schema.heartbeat_interval,
    )

    simulation_manager.create_session(session_id, config)
    return {"status": "started", "session_id": session_id}


@router.post("/step")
async def step_simulation(session_id: str, body: StepRequest | None = None):
    sim = _get_sim(session_id)
    count = body.count if body else 1
    results = sim.step_multiple(count)

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)

    return {
        "tick": sim.clock.now,
        "steps": count,
        "total_events": sum(len(r.events) for r in results),
        "total_delivered": sum(r.messages_delivered for r in results),
        "total_sent": sum(r.messages_sent for r in results),
    }


@router.post("/play")
async def play_simulation(session_id: str):
    from main import simulation_manager
    from engine.clock import ClockMode

    sim = _get_sim(session_id)
    sim.clock.mode = ClockMode.PLAYING
    simulation_manager.start_play_loop(session_id)
    return {"status": "playing"}


@router.post("/pause")
async def pause_simulation(session_id: str):
    from main import simulation_manager
    from engine.clock import ClockMode

    sim = _get_sim(session_id)
    sim.clock.mode = ClockMode.PAUSED
    simulation_manager.stop_play_loop(session_id)
    return {"status": "paused", "tick": sim.clock.now}


@router.put("/speed")
async def set_speed(session_id: str, body: SpeedRequest):
    sim = _get_sim(session_id)
    sim.clock.speed = body.speed
    return {"speed": sim.clock.speed}


@router.get("/state")
async def get_state(session_id: str):
    sim = _get_sim(session_id)
    snapshot = sim.get_snapshot()
    return {
        "tick": snapshot.tick,
        "clock_mode": snapshot.clock_mode,
        "speed": snapshot.speed,
        "nodes": [vars(n) for n in snapshot.nodes],
        "in_flight_messages": snapshot.in_flight_messages,
        "partitions": snapshot.partitions,
        "events_recent": snapshot.events_recent,
    }


@router.get("/events")
async def get_events(session_id: str, from_tick: int = 0, to_tick: int | None = None):
    sim = _get_sim(session_id)
    events = sim.event_log.get_events(from_tick, to_tick)
    return {"events": [e.to_dict() for e in events]}
