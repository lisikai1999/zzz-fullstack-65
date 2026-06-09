from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from raft.node import (
    Action,
    ApplyToStateMachine,
    RaftNode,
    ResetElectionTimer,
    ResetHeartbeatTimer,
    SendMessage,
    TakeSnapshot,
)
from raft.rpc import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    RequestVoteRequest,
    RequestVoteResponse,
)

from .clock import ClockMode, VirtualClock
from .event_log import EventLog, SimulationEvent
from .fault_injector import FaultInjector
from .message_queue import InFlightMessage, MessageQueue
from .network import SimulatedNetwork


@dataclass
class ClusterConfig:
    node_count: int = 5
    base_delay: int = 15
    delay_jitter: int = 10
    packet_loss_rate: float = 0.0
    election_timeout_min: int = 150
    election_timeout_max: int = 300
    heartbeat_interval: int = 50


@dataclass
class NodeSnapshot:
    id: str
    role: str
    alive: bool
    current_term: int
    voted_for: str | None
    log: list[dict]
    log_length: int
    commit_index: int
    last_applied: int
    leader_id: str | None
    next_index: dict[str, int] | None
    match_index: dict[str, int] | None
    snapshot_index: int | None
    snapshot_term: int | None


@dataclass
class ClusterSnapshot:
    tick: int
    clock_mode: str
    speed: float
    nodes: list[NodeSnapshot]
    in_flight_messages: list[dict]
    partitions: list[list[str]]
    events_recent: list[dict]


@dataclass
class StepResult:
    tick: int
    events: list[SimulationEvent]
    messages_delivered: int
    messages_sent: int


class SimulationCluster:
    """Manages the full Raft simulation: nodes + network + clock."""

    def __init__(self, config: ClusterConfig | None = None) -> None:
        self.config = config or ClusterConfig()
        self.clock = VirtualClock()
        self.message_queue = MessageQueue()
        self.network = SimulatedNetwork(self.clock, self.message_queue)
        self.event_log = EventLog()
        self.fault_injector = FaultInjector(self)

        self.nodes: dict[str, RaftNode] = {}
        self.alive_nodes: set[str] = set()
        self.election_timers: dict[str, int] = {}
        self.heartbeat_timers: dict[str, int] = {}

        self.network.configure(
            base_delay=self.config.base_delay,
            jitter=self.config.delay_jitter,
            loss_rate=self.config.packet_loss_rate,
        )

        self._initialize_cluster()

    def _initialize_cluster(self) -> None:
        node_ids = [f"node-{i+1}" for i in range(self.config.node_count)]
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            node = RaftNode(nid, peers)
            self.nodes[nid] = node
            self.alive_nodes.add(nid)

        for nid in node_ids:
            self._schedule_election_timer(nid)

    def _schedule_election_timer(self, node_id: str) -> None:
        if node_id in self.election_timers:
            self.clock.cancel(self.election_timers[node_id])
        timeout = random.randint(
            self.config.election_timeout_min, self.config.election_timeout_max
        )
        event_id = self.clock.schedule_after(timeout, "election_timeout", {"node_id": node_id})
        self.election_timers[node_id] = event_id

    def _schedule_heartbeat_timer(self, node_id: str) -> None:
        if node_id in self.heartbeat_timers:
            self.clock.cancel(self.heartbeat_timers[node_id])
        event_id = self.clock.schedule_after(
            self.config.heartbeat_interval, "heartbeat_timeout", {"node_id": node_id}
        )
        self.heartbeat_timers[node_id] = event_id

    def step(self) -> StepResult:
        """Advance simulation by one tick."""
        events: list[SimulationEvent] = []
        messages_delivered = 0
        messages_sent = 0

        fired = self.clock.tick()

        for event in fired:
            node_id = event.data.get("node_id")
            if node_id and node_id not in self.alive_nodes:
                continue

            if event.callback_name == "election_timeout":
                if node_id and node_id in self.nodes:
                    node = self.nodes[node_id]
                    actions = node.on_election_timeout()
                    events.append(SimulationEvent(
                        tick=self.clock.now,
                        event_type="election_started",
                        source_node=node_id,
                        description=f"{node_id} started election for term {node.current_term}",
                        payload={"term": node.current_term},
                    ))
                    sent = self._process_actions(node_id, actions, events)
                    messages_sent += sent

            elif event.callback_name == "heartbeat_timeout":
                if node_id and node_id in self.nodes:
                    node = self.nodes[node_id]
                    actions = node.on_heartbeat_timeout()
                    sent = self._process_actions(node_id, actions, events)
                    messages_sent += sent

        delivered = self.message_queue.deliverable_at(self.clock.now)
        for msg in delivered:
            if msg.destination not in self.alive_nodes:
                continue
            if not self.network.is_connected(msg.source, msg.destination):
                continue

            dest_node = self.nodes[msg.destination]
            actions = self._deliver_message(dest_node, msg, events)
            messages_delivered += 1
            sent = self._process_actions(msg.destination, actions, events)
            messages_sent += sent

        for ev in events:
            self.event_log.record(ev)

        return StepResult(
            tick=self.clock.now,
            events=events,
            messages_delivered=messages_delivered,
            messages_sent=messages_sent,
        )

    def step_multiple(self, count: int) -> list[StepResult]:
        results = []
        for _ in range(count):
            results.append(self.step())
        return results

    def _deliver_message(self, node: RaftNode, msg: InFlightMessage, events: list[SimulationEvent]) -> list[Action]:
        payload = msg.payload
        actions: list[Action] = []

        if isinstance(payload, RequestVoteRequest):
            resp, acts = node.on_request_vote(payload)
            actions.extend(acts)
            reply_msg = self.network.send(msg.destination, msg.source, resp)
            if reply_msg:
                events.append(SimulationEvent(
                    tick=self.clock.now,
                    event_type="vote_response_sent",
                    source_node=msg.destination,
                    target_node=msg.source,
                    description=f"{msg.destination} {'granted' if resp.vote_granted else 'denied'} vote to {msg.source}",
                    payload={"vote_granted": resp.vote_granted, "term": resp.term},
                ))

        elif isinstance(payload, RequestVoteResponse):
            prev_role = node.role.value
            acts = node.on_request_vote_response(payload, msg.source)
            actions.extend(acts)
            if prev_role != "leader" and node.role.value == "leader":
                events.append(SimulationEvent(
                    tick=self.clock.now,
                    event_type="leader_elected",
                    source_node=node.node_id,
                    description=f"{node.node_id} became leader for term {node.current_term}",
                    payload={"term": node.current_term},
                ))

        elif isinstance(payload, AppendEntriesRequest):
            resp, acts = node.on_append_entries(payload)
            actions.extend(acts)
            reply_msg = self.network.send(msg.destination, msg.source, resp)
            if payload.entries:
                events.append(SimulationEvent(
                    tick=self.clock.now,
                    event_type="entries_received",
                    source_node=msg.source,
                    target_node=msg.destination,
                    description=f"{msg.destination} received {len(payload.entries)} entries from {msg.source}",
                    payload={"count": len(payload.entries), "success": resp.success},
                ))

        elif isinstance(payload, AppendEntriesResponse):
            acts = node.on_append_entries_response(payload, msg.source)
            actions.extend(acts)

        elif isinstance(payload, InstallSnapshotRequest):
            resp, acts = node.on_install_snapshot(payload)
            actions.extend(acts)
            self.network.send(msg.destination, msg.source, resp)

        elif isinstance(payload, InstallSnapshotResponse):
            pass

        return actions

    def _process_actions(self, node_id: str, actions: list[Action], events: list[SimulationEvent]) -> int:
        messages_sent = 0
        for action in actions:
            if isinstance(action, SendMessage):
                sent = self.network.send(node_id, action.to, action.message)
                if sent:
                    messages_sent += 1
                    events.append(SimulationEvent(
                        tick=self.clock.now,
                        event_type="message_sent",
                        source_node=node_id,
                        target_node=action.to,
                        description=f"{node_id} -> {action.to}: {type(action.message).__name__}",
                        payload={"message_type": type(action.message).__name__},
                    ))

            elif isinstance(action, ResetElectionTimer):
                self._schedule_election_timer(node_id)

            elif isinstance(action, ResetHeartbeatTimer):
                self._schedule_heartbeat_timer(node_id)

            elif isinstance(action, ApplyToStateMachine):
                events.append(SimulationEvent(
                    tick=self.clock.now,
                    event_type="command_applied",
                    source_node=node_id,
                    description=f"{node_id} applied: {action.entry.command}",
                    payload={"command": action.entry.command, "index": action.entry.index},
                ))

            elif isinstance(action, TakeSnapshot):
                node = self.nodes[node_id]
                node.log.compact_up_to(action.up_to_index, dict(node.state_machine))
                events.append(SimulationEvent(
                    tick=self.clock.now,
                    event_type="snapshot_taken",
                    source_node=node_id,
                    description=f"{node_id} compacted log up to index {action.up_to_index}",
                    payload={"up_to_index": action.up_to_index, "term": node.log.snapshot.last_included_term if node.log.snapshot else 0},
                ))

        return messages_sent

    def propose_command(self, node_id: str, command: str) -> bool:
        if node_id not in self.alive_nodes:
            return False
        node = self.nodes[node_id]
        actions = node.propose_command(command)
        if not actions:
            return False
        events: list[SimulationEvent] = []
        events.append(SimulationEvent(
            tick=self.clock.now,
            event_type="command_proposed",
            source_node=node_id,
            description=f"Client proposed '{command}' to {node_id}",
            payload={"command": command},
        ))
        self._process_actions(node_id, actions, events)
        for ev in events:
            self.event_log.record(ev)
        return True

    def get_snapshot(self) -> ClusterSnapshot:
        nodes = []
        for nid, node in self.nodes.items():
            snap = node.log.snapshot
            ns = NodeSnapshot(
                id=nid,
                role=node.role.value,
                alive=nid in self.alive_nodes,
                current_term=node.current_term,
                voted_for=node.voted_for,
                log=[e.to_dict() for e in node.log.all_entries()],
                log_length=node.log.last_index,
                commit_index=node.commit_index,
                last_applied=node.last_applied,
                leader_id=node.leader_id,
                next_index=dict(node.leader_state.next_index) if node.leader_state else None,
                match_index=dict(node.leader_state.match_index) if node.leader_state else None,
                snapshot_index=snap.last_included_index if snap else None,
                snapshot_term=snap.last_included_term if snap else None,
            )
            nodes.append(ns)

        in_flight = []
        for msg in self.message_queue.all_in_flight():
            in_flight.append({
                "id": msg.message_id,
                "from": msg.source,
                "to": msg.destination,
                "message_type": msg.message_type,
                "send_tick": msg.send_tick,
                "deliver_tick": msg.deliver_tick,
            })

        return ClusterSnapshot(
            tick=self.clock.now,
            clock_mode=self.clock.mode.value,
            speed=self.clock.speed,
            nodes=nodes,
            in_flight_messages=in_flight,
            partitions=self.network.get_partitions(),
            events_recent=[e.to_dict() for e in self.event_log.get_recent(30)],
        )
