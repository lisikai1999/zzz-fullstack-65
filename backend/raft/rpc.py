from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .state import LogEntry


@dataclass
class RequestVoteRequest:
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class RequestVoteResponse:
    term: int
    vote_granted: bool


@dataclass
class AppendEntriesRequest:
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry] = field(default_factory=list)
    leader_commit: int = 0


@dataclass
class AppendEntriesResponse:
    term: int
    success: bool
    conflict_term: Optional[int] = None
    conflict_index: Optional[int] = None


@dataclass
class InstallSnapshotRequest:
    term: int
    leader_id: str
    last_included_index: int
    last_included_term: int
    data: dict = field(default_factory=dict)


@dataclass
class InstallSnapshotResponse:
    term: int


RpcMessage = (
    RequestVoteRequest
    | RequestVoteResponse
    | AppendEntriesRequest
    | AppendEntriesResponse
    | InstallSnapshotRequest
    | InstallSnapshotResponse
)
