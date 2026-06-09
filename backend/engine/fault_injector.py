from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cluster import SimulationCluster


class FaultInjector:
    """Provides fault injection methods for the simulation."""

    def __init__(self, cluster: SimulationCluster) -> None:
        self._cluster = cluster

    def kill_node(self, node_id: str) -> bool:
        if node_id not in self._cluster.nodes:
            return False
        if node_id not in self._cluster.alive_nodes:
            return False
        self._cluster.alive_nodes.discard(node_id)
        if node_id in self._cluster.election_timers:
            self._cluster.clock.cancel(self._cluster.election_timers[node_id])
            del self._cluster.election_timers[node_id]
        if node_id in self._cluster.heartbeat_timers:
            self._cluster.clock.cancel(self._cluster.heartbeat_timers[node_id])
            del self._cluster.heartbeat_timers[node_id]
        self._cluster.message_queue.remove_messages_involving(node_id)
        return True

    def restart_node(self, node_id: str) -> bool:
        if node_id not in self._cluster.nodes:
            return False
        if node_id in self._cluster.alive_nodes:
            return False
        self._cluster.alive_nodes.add(node_id)
        node = self._cluster.nodes[node_id]
        node.role = node.role.FOLLOWER
        node.leader_state = None
        node.votes_received = set()
        # Recover commit/applied progress from persistent log.
        # Per Raft paper: log is persistent, so commit_index can be
        # recovered up to what we know is safely committed (last_applied
        # was already applied before crash, log entries are durable).
        snapshot = node.log.snapshot
        if snapshot:
            node.commit_index = max(node.commit_index, snapshot.last_included_index)
            node.last_applied = max(node.last_applied, snapshot.last_included_index)
        # Keep commit_index/last_applied from before the crash — they reflect
        # durable state. The leader will update commit_index via AppendEntries.
        self._cluster._schedule_election_timer(node_id)
        return True

    def drop_next_message(self, from_id: str, to_id: str) -> None:
        self._cluster.network.schedule_drop_next(from_id, to_id)

    def duplicate_next_message(self, from_id: str, to_id: str) -> None:
        self._cluster.network.schedule_duplicate_next(from_id, to_id)

    def partition(self, group_a: list[str], group_b: list[str]) -> None:
        self._cluster.network.create_partition(group_a, group_b)
        from .event_log import SimulationEvent
        self._cluster.event_log.record(SimulationEvent(
            tick=self._cluster.clock.now,
            event_type="partition_created",
            description=f"Partition: {group_a} | {group_b}",
            payload={"group_a": group_a, "group_b": group_b},
        ))

    def heal_partition(self) -> None:
        self._cluster.network.heal_all_partitions()
        from .event_log import SimulationEvent
        self._cluster.event_log.record(SimulationEvent(
            tick=self._cluster.clock.now,
            event_type="partition_healed",
            description="All partitions healed",
        ))

    def heal_link(self, node_a: str, node_b: str) -> bool:
        """Reconnect a single link between two nodes."""
        healed = self._cluster.network.heal_link(node_a, node_b)
        if healed:
            from .event_log import SimulationEvent
            self._cluster.event_log.record(SimulationEvent(
                tick=self._cluster.clock.now,
                event_type="link_healed",
                source_node=node_a,
                target_node=node_b,
                description=f"Link restored: {node_a} <-> {node_b}",
                payload={"node_a": node_a, "node_b": node_b},
            ))
        return healed
