from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from .log import RaftLog
from .rpc import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    RequestVoteRequest,
    RequestVoteResponse,
    RpcMessage,
)
from .snapshot import Snapshot
from .state import LeaderVolatileState, LogEntry, Role


# --- Action types returned by RaftNode methods ---


@dataclass
class SendMessage:
    to: str
    message: RpcMessage


@dataclass
class ResetElectionTimer:
    pass


@dataclass
class ResetHeartbeatTimer:
    pass


@dataclass
class ApplyToStateMachine:
    entry: LogEntry


@dataclass
class TakeSnapshot:
    up_to_index: int


Action = Union[SendMessage, ResetElectionTimer, ResetHeartbeatTimer, ApplyToStateMachine, TakeSnapshot]


class RaftNode:
    """A single Raft node. Pure state machine — no I/O, no timers.

    Every handler returns a list of Action objects that the simulation
    engine must execute. This makes the node fully deterministic and testable.
    """

    SNAPSHOT_THRESHOLD = 100

    def __init__(self, node_id: str, peers: list[str]) -> None:
        self.node_id = node_id
        self.peers = list(peers)

        self.role = Role.FOLLOWER
        self.current_term = 0
        self.voted_for: str | None = None
        self.log = RaftLog()

        self.commit_index = 0
        self.last_applied = 0

        self.leader_state: LeaderVolatileState | None = None
        self.votes_received: set[str] = set()
        self.leader_id: str | None = None

        self.state_machine: dict[str, str] = {}

    @property
    def majority(self) -> int:
        return (len(self.peers) + 1) // 2 + 1

    # --- Timer-driven transitions ---

    def on_election_timeout(self) -> list[Action]:
        """Called when election timer fires. Start a new election."""
        if self.role == Role.LEADER:
            return []
        return self._start_election()

    def on_heartbeat_timeout(self) -> list[Action]:
        """Called when heartbeat timer fires (leader only). Send AppendEntries to all."""
        if self.role != Role.LEADER:
            return []
        actions: list[Action] = [ResetHeartbeatTimer()]
        for peer in self.peers:
            actions.extend(self._send_append_entries(peer))
        return actions

    # --- RPC handlers ---

    def on_request_vote(self, req: RequestVoteRequest) -> tuple[RequestVoteResponse, list[Action]]:
        actions: list[Action] = []

        if req.term > self.current_term:
            actions.extend(self._step_down(req.term))

        grant = False
        if req.term >= self.current_term:
            if self.voted_for is None or self.voted_for == req.candidate_id:
                if self._is_log_up_to_date(req.last_log_index, req.last_log_term):
                    grant = True
                    self.voted_for = req.candidate_id
                    actions.append(ResetElectionTimer())

        resp = RequestVoteResponse(term=self.current_term, vote_granted=grant)
        return resp, actions

    def on_append_entries(self, req: AppendEntriesRequest) -> tuple[AppendEntriesResponse, list[Action]]:
        actions: list[Action] = []

        if req.term < self.current_term:
            return AppendEntriesResponse(term=self.current_term, success=False), actions

        if req.term > self.current_term or self.role != Role.FOLLOWER:
            actions.extend(self._step_down(req.term))

        self.leader_id = req.leader_id
        actions.append(ResetElectionTimer())

        success = self.log.append_entries(req.prev_log_index, req.prev_log_term, req.entries)

        if not success:
            conflict_term, conflict_index = self.log.find_conflict_info(req.prev_log_index)
            return (
                AppendEntriesResponse(
                    term=self.current_term,
                    success=False,
                    conflict_term=conflict_term,
                    conflict_index=conflict_index,
                ),
                actions,
            )

        if req.leader_commit > self.commit_index:
            new_commit = min(req.leader_commit, self.log.last_index)
            if new_commit > self.commit_index:
                self.commit_index = new_commit
                actions.extend(self._apply_committed())

        return AppendEntriesResponse(term=self.current_term, success=True), actions

    def on_request_vote_response(self, resp: RequestVoteResponse, from_id: str) -> list[Action]:
        if resp.term > self.current_term:
            return self._step_down(resp.term)

        if self.role != Role.CANDIDATE:
            return []

        if resp.vote_granted:
            self.votes_received.add(from_id)
            if len(self.votes_received) >= self.majority:
                return self._become_leader()

        return []

    def on_append_entries_response(self, resp: AppendEntriesResponse, from_id: str) -> list[Action]:
        if resp.term > self.current_term:
            return self._step_down(resp.term)

        if self.role != Role.LEADER or self.leader_state is None:
            return []

        actions: list[Action] = []

        if resp.success:
            # The follower accepted everything we sent. We sent entries from
            # prev_log_index+1 to our last_index. The follower now has up to
            # at least our log's last_index (at the time we sent).
            # Safe approximation: set match to our current last_index since
            # we only append entries and the follower confirmed acceptance.
            new_match = self.log.last_index
            if new_match > self.leader_state.match_index.get(from_id, 0):
                self.leader_state.match_index[from_id] = new_match
            self.leader_state.next_index[from_id] = new_match + 1

            actions.extend(self._advance_commit_index())
        else:
            if resp.conflict_index is not None:
                self.leader_state.next_index[from_id] = resp.conflict_index
            else:
                self.leader_state.next_index[from_id] = max(
                    1, self.leader_state.next_index[from_id] - 1
                )
            actions.extend(self._send_append_entries(from_id))

        return actions

    def on_install_snapshot(self, req: InstallSnapshotRequest) -> tuple[InstallSnapshotResponse, list[Action]]:
        actions: list[Action] = []

        if req.term < self.current_term:
            return InstallSnapshotResponse(term=self.current_term), actions

        if req.term > self.current_term or self.role != Role.FOLLOWER:
            actions.extend(self._step_down(req.term))

        actions.append(ResetElectionTimer())
        self.leader_id = req.leader_id

        snapshot = Snapshot(
            last_included_index=req.last_included_index,
            last_included_term=req.last_included_term,
            state_machine_state=req.data,
        )
        self.log.install_snapshot(snapshot)
        self.state_machine = dict(req.data)

        if req.last_included_index > self.commit_index:
            self.commit_index = req.last_included_index
        if req.last_included_index > self.last_applied:
            self.last_applied = req.last_included_index

        return InstallSnapshotResponse(term=self.current_term), actions

    # --- Client interface ---

    def propose_command(self, command: str) -> list[Action]:
        """Submit a client command. Only valid on leader."""
        if self.role != Role.LEADER:
            return []

        entry = self.log.append_new(self.current_term, command)

        actions: list[Action] = []
        for peer in self.peers:
            actions.extend(self._send_append_entries(peer))
        return actions

    # --- State serialization ---

    def get_snapshot(self) -> dict:
        return {
            "id": self.node_id,
            "role": self.role.value,
            "current_term": self.current_term,
            "voted_for": self.voted_for,
            "log": [e.to_dict() for e in self.log.all_entries()],
            "log_length": self.log.last_index,
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "leader_id": self.leader_id,
            "next_index": dict(self.leader_state.next_index) if self.leader_state else None,
            "match_index": dict(self.leader_state.match_index) if self.leader_state else None,
        }

    # --- Private helpers ---

    def _start_election(self) -> list[Action]:
        self.current_term += 1
        self.role = Role.CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.leader_id = None

        actions: list[Action] = [ResetElectionTimer()]

        req = RequestVoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.log.last_index,
            last_log_term=self.log.last_term,
        )
        for peer in self.peers:
            actions.append(SendMessage(to=peer, message=req))

        if self.majority == 1:
            actions.extend(self._become_leader())

        return actions

    def _become_leader(self) -> list[Action]:
        self.role = Role.LEADER
        self.leader_id = self.node_id
        self.leader_state = LeaderVolatileState(
            next_index={peer: self.log.last_index + 1 for peer in self.peers},
            match_index={peer: 0 for peer in self.peers},
        )

        actions: list[Action] = [ResetHeartbeatTimer()]
        for peer in self.peers:
            actions.extend(self._send_append_entries(peer))
        return actions

    def _step_down(self, new_term: int) -> list[Action]:
        self.current_term = new_term
        self.role = Role.FOLLOWER
        self.voted_for = None
        self.leader_state = None
        self.votes_received = set()
        return [ResetElectionTimer()]

    def _send_append_entries(self, peer: str) -> list[Action]:
        if self.leader_state is None:
            return []

        next_idx = self.leader_state.next_index[peer]

        if self.log.snapshot and next_idx <= self.log.snapshot.last_included_index:
            req = InstallSnapshotRequest(
                term=self.current_term,
                leader_id=self.node_id,
                last_included_index=self.log.snapshot.last_included_index,
                last_included_term=self.log.snapshot.last_included_term,
                data=self.log.snapshot.state_machine_state,
            )
            return [SendMessage(to=peer, message=req)]

        prev_index = next_idx - 1
        prev_term = self.log.get_term_at(prev_index)
        entries = self.log.get_entries_from(next_idx)

        req = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.node_id,
            prev_log_index=prev_index,
            prev_log_term=prev_term,
            entries=entries,
            leader_commit=self.commit_index,
        )
        return [SendMessage(to=peer, message=req)]

    def _advance_commit_index(self) -> list[Action]:
        if self.leader_state is None:
            return []

        for n in range(self.log.last_index, self.commit_index, -1):
            term_at_n = self.log.get_term_at(n)
            if term_at_n != self.current_term:
                continue
            replication_count = 1
            for peer in self.peers:
                if self.leader_state.match_index.get(peer, 0) >= n:
                    replication_count += 1
            if replication_count >= self.majority:
                self.commit_index = n
                return self._apply_committed()

        return []

    def _apply_committed(self) -> list[Action]:
        actions: list[Action] = []
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log.get_entry(self.last_applied)
            if entry:
                self._apply_entry(entry)
                actions.append(ApplyToStateMachine(entry=entry))

        if self.last_applied - (self.log.snapshot.last_included_index if self.log.snapshot else 0) >= self.SNAPSHOT_THRESHOLD:
            actions.append(TakeSnapshot(up_to_index=self.last_applied))

        return actions

    def _apply_entry(self, entry: LogEntry) -> None:
        parts = entry.command.split("=", 1)
        if len(parts) == 2:
            key, value = parts
            self.state_machine[key.strip()] = value.strip()

    def _is_log_up_to_date(self, candidate_last_index: int, candidate_last_term: int) -> bool:
        my_last_term = self.log.last_term
        if candidate_last_term != my_last_term:
            return candidate_last_term > my_last_term
        return candidate_last_index >= self.log.last_index

