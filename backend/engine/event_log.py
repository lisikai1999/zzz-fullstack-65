from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationEvent:
    tick: int
    event_type: str
    source_node: str | None = None
    target_node: str | None = None
    description: str = ""
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "event_type": self.event_type,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "description": self.description,
            "payload": self.payload,
        }


class EventLog:
    """Records simulation events for replay and timeline display."""

    def __init__(self, max_size: int = 10000) -> None:
        self._events: list[SimulationEvent] = []
        self._max_size = max_size

    def record(self, event: SimulationEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_size:
            self._events = self._events[-self._max_size:]

    def get_events(self, from_tick: int = 0, to_tick: int | None = None) -> list[SimulationEvent]:
        result = []
        for e in self._events:
            if e.tick < from_tick:
                continue
            if to_tick is not None and e.tick > to_tick:
                break
            result.append(e)
        return result

    def get_recent(self, count: int = 50) -> list[SimulationEvent]:
        return self._events[-count:]

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)
