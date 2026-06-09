from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import heapq


class ClockMode(str, Enum):
    PAUSED = "paused"
    PLAYING = "playing"
    STEPPING = "stepping"


@dataclass(order=True)
class ScheduledEvent:
    fire_tick: int
    event_id: int = field(compare=True)
    callback_name: str = field(compare=False)
    data: dict = field(default_factory=dict, compare=False)
    cancelled: bool = field(default=False, compare=False)


class VirtualClock:
    """Discrete-event simulation clock. Time advances only when explicitly ticked.
    1 tick = 1ms virtual time.
    """

    def __init__(self) -> None:
        self._current_tick: int = 0
        self._mode: ClockMode = ClockMode.PAUSED
        self._speed: float = 1.0
        self._event_heap: list[ScheduledEvent] = []
        self._next_event_id: int = 0

    @property
    def now(self) -> int:
        return self._current_tick

    @property
    def mode(self) -> ClockMode:
        return self._mode

    @mode.setter
    def mode(self, value: ClockMode) -> None:
        self._mode = value

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        self._speed = max(0.1, min(100.0, value))

    def schedule_at(self, tick: int, callback_name: str, data: dict | None = None) -> int:
        event_id = self._next_event_id
        self._next_event_id += 1
        event = ScheduledEvent(
            fire_tick=max(tick, self._current_tick + 1),
            event_id=event_id,
            callback_name=callback_name,
            data=data or {},
        )
        heapq.heappush(self._event_heap, event)
        return event_id

    def schedule_after(self, delay: int, callback_name: str, data: dict | None = None) -> int:
        return self.schedule_at(self._current_tick + delay, callback_name, data)

    def cancel(self, event_id: int) -> None:
        for event in self._event_heap:
            if event.event_id == event_id:
                event.cancelled = True
                break

    def tick(self) -> list[ScheduledEvent]:
        """Advance clock by 1 tick. Returns events that fire at this tick."""
        self._current_tick += 1
        return self._pop_fired_events()

    def advance_to(self, target_tick: int) -> list[ScheduledEvent]:
        """Advance clock to target, collecting all fired events."""
        fired: list[ScheduledEvent] = []
        while self._current_tick < target_tick:
            self._current_tick += 1
            fired.extend(self._pop_fired_events())
        return fired

    def peek_next_event_tick(self) -> int | None:
        """Return the tick of the next scheduled (non-cancelled) event."""
        while self._event_heap and self._event_heap[0].cancelled:
            heapq.heappop(self._event_heap)
        if self._event_heap:
            return self._event_heap[0].fire_tick
        return None

    def _pop_fired_events(self) -> list[ScheduledEvent]:
        fired: list[ScheduledEvent] = []
        while self._event_heap and self._event_heap[0].fire_tick <= self._current_tick:
            event = heapq.heappop(self._event_heap)
            if not event.cancelled:
                fired.append(event)
        return fired
