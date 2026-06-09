from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Snapshot:
    last_included_index: int
    last_included_term: int
    state_machine_state: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "last_included_index": self.last_included_index,
            "last_included_term": self.last_included_term,
            "state_machine_state": self.state_machine_state,
        }
