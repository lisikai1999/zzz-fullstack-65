from dataclasses import dataclass


@dataclass
class SessionModel:
    id: str
    name: str
    node_count: int
    config_json: str
    created_at: str
    updated_at: str


@dataclass
class EventModel:
    id: int
    session_id: str
    tick: int
    event_type: str
    source_node: str | None
    target_node: str | None
    payload_json: str
    description: str


@dataclass
class SnapshotModel:
    id: int
    session_id: str
    tick: int
    state_json: str
