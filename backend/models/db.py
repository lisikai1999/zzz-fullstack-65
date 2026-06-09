import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.environ.get("RAFT_DB_PATH", "raft_sim.db")

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


def init_db() -> None:
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            node_count INTEGER NOT NULL DEFAULT 5,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            tick INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            source_node TEXT,
            target_node TEXT,
            payload_json TEXT DEFAULT '{}',
            description TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_events_session_tick ON events(session_id, tick);

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            tick INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            UNIQUE(session_id, tick)
        );
    """)
    conn.commit()


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
