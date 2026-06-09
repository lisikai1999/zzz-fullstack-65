from fastapi import APIRouter, HTTPException

from models.schemas import NetworkConfigUpdate, PartitionRequest, ProposeRequest, FaultRequest, HealLinkRequest

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["cluster"])


def _get_sim(session_id: str):
    from main import simulation_manager
    sim = simulation_manager.get_session(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found. Call /start first.")
    return sim


@router.post("/nodes/{node_id}/kill")
async def kill_node(session_id: str, node_id: str):
    sim = _get_sim(session_id)
    success = sim.fault_injector.kill_node(node_id)
    if not success:
        raise HTTPException(status_code=400, detail="Node not found or already dead")

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "killed", "node_id": node_id}


@router.post("/nodes/{node_id}/restart")
async def restart_node(session_id: str, node_id: str):
    sim = _get_sim(session_id)
    success = sim.fault_injector.restart_node(node_id)
    if not success:
        raise HTTPException(status_code=400, detail="Node not found or already alive")

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "restarted", "node_id": node_id}


@router.post("/nodes/{node_id}/propose")
async def propose_command(session_id: str, node_id: str, body: ProposeRequest):
    sim = _get_sim(session_id)
    success = sim.propose_command(node_id, body.command)
    if not success:
        raise HTTPException(status_code=400, detail="Node is not the leader or is dead")

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "proposed", "command": body.command}


@router.post("/network/partition")
async def create_partition(session_id: str, body: PartitionRequest):
    sim = _get_sim(session_id)
    sim.fault_injector.partition(body.group_a, body.group_b)

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "partitioned", "group_a": body.group_a, "group_b": body.group_b}


@router.post("/network/heal")
async def heal_partition(session_id: str):
    sim = _get_sim(session_id)
    sim.fault_injector.heal_partition()

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "healed"}


@router.post("/network/heal-link")
async def heal_link(session_id: str, body: HealLinkRequest):
    sim = _get_sim(session_id)
    success = sim.fault_injector.heal_link(body.node_a, body.node_b)
    if not success:
        raise HTTPException(status_code=400, detail="Link is not partitioned")

    from main import simulation_manager
    await simulation_manager.broadcast(session_id)
    return {"status": "link_healed", "node_a": body.node_a, "node_b": body.node_b}


@router.put("/network/config")
async def update_network_config(session_id: str, body: NetworkConfigUpdate):
    sim = _get_sim(session_id)
    sim.network.configure(
        base_delay=body.base_delay,
        jitter=body.delay_jitter,
        loss_rate=body.packet_loss_rate,
    )
    return {"status": "updated"}


@router.post("/fault/drop-message")
async def drop_message(session_id: str, body: FaultRequest):
    sim = _get_sim(session_id)
    sim.network.schedule_drop_next(body.from_node, body.to_node)
    return {"status": "scheduled", "action": "drop"}


@router.post("/fault/duplicate-message")
async def duplicate_message(session_id: str, body: FaultRequest):
    sim = _get_sim(session_id)
    sim.network.schedule_duplicate_next(body.from_node, body.to_node)
    return {"status": "scheduled", "action": "duplicate"}
