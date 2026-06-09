from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    term: int
    index: int
    command: str

    def to_dict(self) -> dict:
        return {"term": self.term, "index": self.index, "command": self.command}


@dataclass
class PersistentState:
    current_term: int = 0
    voted_for: Optional[str] = None
    log: list[LogEntry] = field(default_factory=list)


@dataclass
class VolatileState:
    commit_index: int = 0
    last_applied: int = 0


@dataclass
class LeaderVolatileState:
    next_index: dict[str, int] = field(default_factory=dict)
    match_index: dict[str, int] = field(default_factory=dict)
