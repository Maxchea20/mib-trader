"""Persistent local SQLite market-data database.

This is the persistent local store for candle history. It remains available
locally even when the trading UI is closed so analysis engines can access
persistent market history. Core market history is NOT stored in any cloud DB.
"""
import os
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional

_DB_PATH = os.environ.get("MARKET_DB_PATH", str(Path(__file__).resolve().parents[2] / "market_data.db"))
_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
    return _conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                symbol     TEXT    NOT NULL,
                timeframe  TEXT    NOT NULL,
                ts         INTEGER NOT NULL,
                open       REAL    NOT NULL,
                high       REAL    NOT NULL,
                low        REAL    NOT NULL,
                close      REAL    NOT NULL,
                volume     REAL    NOT NULL,
                PRIMARY KEY (symbol, timeframe, ts)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol, timeframe, ts);"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_meta (
                symbol      TEXT NOT NULL,
                timeframe   TEXT NOT NULL,
                last_sync   INTEGER,
                last_status TEXT,
                PRIMARY KEY (symbol, timeframe)
            );
            """
        )
        conn.commit()


def upsert_candles(symbol: str, timeframe: str, candles: List[Dict]) -> int:
    if not candles:
        return 0
    rows = [
        (symbol, timeframe, int(c["ts"]), float(c["open"]), float(c["high"]),
         float(c["low"]), float(c["close"]), float(c["volume"]))
        for c in candles
    ]
    with _lock:
        conn = _connect()
        conn.executemany(
            """
            INSERT INTO candles(symbol, timeframe, ts, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, timeframe, ts) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume;
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def get_candles(symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "SELECT ts, open, high, low, close, volume FROM candles "
            "WHERE symbol=? AND timeframe=? ORDER BY ts DESC LIMIT ?",
            (symbol, timeframe, limit),
        )
        rows = cur.fetchall()
    rows = list(reversed(rows))
    return [dict(r) for r in rows]


def count_candles(symbol: str, timeframe: str) -> int:
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM candles WHERE symbol=? AND timeframe=?",
            (symbol, timeframe),
        )
        return int(cur.fetchone()["c"])


def bounds(symbol: str, timeframe: str):
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "SELECT MIN(ts) AS mn, MAX(ts) AS mx FROM candles WHERE symbol=? AND timeframe=?",
            (symbol, timeframe),
        )
        r = cur.fetchone()
        return (r["mn"], r["mx"])


def set_sync_meta(symbol: str, timeframe: str, ts: int, status: str) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO sync_meta(symbol, timeframe, last_sync, last_status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, timeframe) DO UPDATE SET
                last_sync=excluded.last_sync, last_status=excluded.last_status;
            """,
            (symbol, timeframe, ts, status),
        )
        conn.commit()


def get_sync_meta(symbol: str, timeframe: str):
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "SELECT last_sync, last_status FROM sync_meta WHERE symbol=? AND timeframe=?",
            (symbol, timeframe),
        )
        r = cur.fetchone()
        return dict(r) if r else {"last_sync": None, "last_status": None}


def db_path() -> str:
    return _DB_PATH
