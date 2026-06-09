import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.db import get_db
from models.schemas import SessionCreate, SessionResponse, ClusterConfigSchema

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def create_session(body: SessionCreate):
    session_id = str(uuid.uuid4())
    config_json = body.config.model_dump_json()
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id, name, node_count, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, body.name, body.config.node_count, config_json, now, now),
        )

    return SessionResponse(
        id=session_id,
        name=body.name,
        node_count=body.config.node_count,
        config=body.config,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=list[SessionResponse])
def list_sessions():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()

    results = []
    for row in rows:
        config = ClusterConfigSchema.model_validate_json(row["config_json"])
        results.append(SessionResponse(
            id=row["id"],
            name=row["name"],
            node_count=row["node_count"],
            config=config,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        ))
    return results


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    config = ClusterConfigSchema.model_validate_json(row["config_json"])
    return SessionResponse(
        id=row["id"],
        name=row["name"],
        node_count=row["node_count"],
        config=config,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{session_id}")
def delete_session(session_id: str):
    with get_db() as conn:
        result = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")

    from main import simulation_manager
    simulation_manager.remove_session(session_id)
    return {"status": "deleted"}
