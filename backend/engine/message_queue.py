from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any
import uuid


@dataclass(order=True)
class InFlightMessage:
    deliver_tick: int
    message_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = field(compare=False, default="")
    destination: str = field(compare=False, default="")
    payload: Any = field(compare=False, default=None)
    send_tick: int = field(compare=False, default=0)
    message_type: str = field(compare=False, default="")


class MessageQueue:
    """Priority queue of in-flight messages, sorted by delivery tick."""

    def __init__(self) -> None:
        self._queue: list[InFlightMessage] = []

    def enqueue(self, msg: InFlightMessage) -> None:
        heapq.heappush(self._queue, msg)

    def deliverable_at(self, tick: int) -> list[InFlightMessage]:
        """Pop and return all messages with deliver_tick <= tick."""
        result: list[InFlightMessage] = []
        while self._queue and self._queue[0].deliver_tick <= tick:
            result.append(heapq.heappop(self._queue))
        return result

    def peek_next_delivery_tick(self) -> int | None:
        return self._queue[0].deliver_tick if self._queue else None

    def all_in_flight(self) -> list[InFlightMessage]:
        return list(self._queue)

    def remove_messages_involving(self, node_id: str) -> list[InFlightMessage]:
        removed = [m for m in self._queue if m.source == node_id or m.destination == node_id]
        self._queue = [m for m in self._queue if m.source != node_id and m.destination != node_id]
        heapq.heapify(self._queue)
        return removed

    def __len__(self) -> int:
        return len(self._queue)
