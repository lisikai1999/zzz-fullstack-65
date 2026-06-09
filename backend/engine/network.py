from __future__ import annotations

import random
import uuid
from typing import Optional

from .clock import VirtualClock
from .message_queue import InFlightMessage, MessageQueue
from raft.rpc import RpcMessage


class SimulatedNetwork:
    """Simulated network with configurable delay, jitter, packet loss, and partitions."""

    def __init__(self, clock: VirtualClock, message_queue: MessageQueue) -> None:
        self._clock = clock
        self._queue = message_queue
        self.base_delay: int = 15
        self.delay_jitter: int = 10
        self.packet_loss_rate: float = 0.0
        self._partitions: set[frozenset[str]] = set()
        self._drop_next: set[tuple[str, str]] = set()
        self._duplicate_next: set[tuple[str, str]] = set()

    def send(self, from_id: str, to_id: str, message: RpcMessage) -> Optional[InFlightMessage]:
        """Attempt to send a message. Returns None if dropped."""
        if not self.is_connected(from_id, to_id):
            return None

        link = (from_id, to_id)
        if link in self._drop_next:
            self._drop_next.discard(link)
            return None

        if random.random() < self.packet_loss_rate:
            return None

        delay = self.base_delay + random.randint(-self.delay_jitter, self.delay_jitter)
        delay = max(1, delay)

        msg_type = type(message).__name__
        msg = InFlightMessage(
            deliver_tick=self._clock.now + delay,
            message_id=str(uuid.uuid4())[:8],
            source=from_id,
            destination=to_id,
            payload=message,
            send_tick=self._clock.now,
            message_type=msg_type,
        )
        self._queue.enqueue(msg)

        if link in self._duplicate_next:
            self._duplicate_next.discard(link)
            dup_delay = delay + random.randint(1, 5)
            dup = InFlightMessage(
                deliver_tick=self._clock.now + dup_delay,
                message_id=str(uuid.uuid4())[:8],
                source=from_id,
                destination=to_id,
                payload=message,
                send_tick=self._clock.now,
                message_type=msg_type,
            )
            self._queue.enqueue(dup)

        return msg

    def is_connected(self, node_a: str, node_b: str) -> bool:
        pair = frozenset([node_a, node_b])
        return pair not in self._partitions

    def set_partition(self, node_a: str, node_b: str, connected: bool) -> None:
        pair = frozenset([node_a, node_b])
        if connected:
            self._partitions.discard(pair)
        else:
            self._partitions.add(pair)

    def create_partition(self, group_a: list[str], group_b: list[str]) -> None:
        """Disconnect all links between group_a and group_b."""
        for a in group_a:
            for b in group_b:
                self._partitions.add(frozenset([a, b]))

    def heal_all_partitions(self) -> None:
        self._partitions.clear()

    def heal_link(self, node_a: str, node_b: str) -> bool:
        """Reconnect a single link. Returns True if it was partitioned."""
        pair = frozenset([node_a, node_b])
        if pair in self._partitions:
            self._partitions.discard(pair)
            return True
        return False

    def get_partitions(self) -> list[list[str]]:
        return [list(p) for p in self._partitions]

    def schedule_drop_next(self, from_id: str, to_id: str) -> None:
        self._drop_next.add((from_id, to_id))

    def schedule_duplicate_next(self, from_id: str, to_id: str) -> None:
        self._duplicate_next.add((from_id, to_id))

    def configure(self, base_delay: int | None = None, jitter: int | None = None, loss_rate: float | None = None) -> None:
        if base_delay is not None:
            self.base_delay = max(1, base_delay)
        if jitter is not None:
            self.delay_jitter = max(0, jitter)
        if loss_rate is not None:
            self.packet_loss_rate = max(0.0, min(1.0, loss_rate))
