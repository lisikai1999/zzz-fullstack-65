from __future__ import annotations

from typing import Optional

from .state import LogEntry
from .snapshot import Snapshot


class RaftLog:
    """Raft log with compaction support.

    After compaction, entries before the snapshot are discarded.
    `_offset` tracks the index of the first entry in `_entries`
    so that logical indices remain consistent.
    """

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []
        self._snapshot: Optional[Snapshot] = None
        self._offset: int = 0

    @property
    def snapshot(self) -> Optional[Snapshot]:
        return self._snapshot

    @property
    def last_index(self) -> int:
        if self._entries:
            return self._entries[-1].index
        if self._snapshot:
            return self._snapshot.last_included_index
        return 0

    @property
    def last_term(self) -> int:
        if self._entries:
            return self._entries[-1].term
        if self._snapshot:
            return self._snapshot.last_included_term
        return 0

    def __len__(self) -> int:
        return len(self._entries)

    def get_entry(self, index: int) -> Optional[LogEntry]:
        if index <= 0:
            return None
        pos = index - self._offset - 1
        if 0 <= pos < len(self._entries):
            return self._entries[pos]
        return None

    def get_term_at(self, index: int) -> int:
        if index == 0:
            return 0
        if self._snapshot and index == self._snapshot.last_included_index:
            return self._snapshot.last_included_term
        entry = self.get_entry(index)
        return entry.term if entry else 0

    def get_entries_from(self, start_index: int) -> list[LogEntry]:
        if start_index <= self._offset:
            start_index = self._offset + 1
        pos = start_index - self._offset - 1
        if pos < 0:
            pos = 0
        return self._entries[pos:]

    def append(self, entry: LogEntry) -> None:
        self._entries.append(entry)

    def append_new(self, term: int, command: str) -> LogEntry:
        index = self.last_index + 1
        entry = LogEntry(term=term, index=index, command=command)
        self._entries.append(entry)
        return entry

    def truncate_from(self, index: int) -> None:
        """Remove all entries at `index` and beyond."""
        pos = index - self._offset - 1
        if 0 <= pos < len(self._entries):
            self._entries = self._entries[:pos]

    def append_entries(self, prev_index: int, prev_term: int, entries: list[LogEntry]) -> bool:
        """Consistency check and append. Returns True on success."""
        if prev_index > 0:
            if prev_index < self._offset:
                return False
            actual_term = self.get_term_at(prev_index)
            if actual_term != prev_term:
                return False

        for entry in entries:
            existing = self.get_entry(entry.index)
            if existing:
                if existing.term != entry.term:
                    self.truncate_from(entry.index)
                    self.append(entry)
            else:
                self.append(entry)
        return True

    def find_conflict_info(self, prev_index: int) -> tuple[Optional[int], int]:
        """Return (conflict_term, conflict_index) for fast backup optimization."""
        entry = self.get_entry(prev_index)
        if entry is None:
            return None, self.last_index + 1
        conflict_term = entry.term
        conflict_index = prev_index
        while conflict_index > self._offset + 1:
            prev_entry = self.get_entry(conflict_index - 1)
            if prev_entry is None or prev_entry.term != conflict_term:
                break
            conflict_index -= 1
        return conflict_term, conflict_index

    def compact_up_to(self, index: int, state: dict) -> Snapshot:
        """Discard entries up to `index`, replacing with a snapshot."""
        term = self.get_term_at(index)
        self._snapshot = Snapshot(
            last_included_index=index,
            last_included_term=term,
            state_machine_state=state,
        )
        pos = index - self._offset
        self._entries = self._entries[pos:]
        self._offset = index
        return self._snapshot

    def install_snapshot(self, snapshot: Snapshot) -> None:
        """Replace log with a snapshot from the leader."""
        self._snapshot = snapshot
        self._offset = snapshot.last_included_index
        self._entries = [
            e for e in self._entries if e.index > snapshot.last_included_index
        ]

    def all_entries(self) -> list[LogEntry]:
        return list(self._entries)
