"""Paper trading engine with persistent SQLite history.

Stores every paper trade (open + closed) so results can be reviewed later. Open
positions are marked-to-market against the live price and auto-closed when price
hits the stop-loss (SL) or take-profit (TP). This is simulated only — no real
orders, no fees/slippage modelled.
"""
import time
import uuid
import sqlite3
import threading
from typing import Dict, List, Optional

from .market_data import database as mdb

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None

LONG = "LONG"
SHORT = "SHORT"


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(mdb.db_path(), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
    return _conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                id            TEXT PRIMARY KEY,
                symbol        TEXT NOT NULL,
                timeframe     TEXT,
                side          TEXT NOT NULL,
                status        TEXT NOT NULL,
                entry_price   REAL NOT NULL,
                sl_price      REAL,
                tp_price      REAL,
                qty           REAL NOT NULL,
                notional_usd  REAL NOT NULL,
                opened_at     INTEGER NOT NULL,
                closed_at     INTEGER,
                exit_price    REAL,
                exit_reason   TEXT,
                pnl           REAL,
                pnl_pct       REAL,
                brain_state   TEXT,
                consensus     REAL,
                confidence    REAL,
                note          TEXT,
                source        TEXT DEFAULT 'MANUAL'
            );
            """
        )
        # migration for pre-existing DBs
        try:
            conn.execute("ALTER TABLE paper_trades ADD COLUMN source TEXT DEFAULT 'MANUAL'")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def _row_to_dict(r: sqlite3.Row) -> Dict:
    return {k: r[k] for k in r.keys()}


def _pnl(side: str, entry: float, exit_price: float, qty: float):
    if side == LONG:
        pnl = (exit_price - entry) * qty
        pct = (exit_price - entry) / entry * 100.0
    else:
        pnl = (entry - exit_price) * qty
        pct = (entry - exit_price) / entry * 100.0
    return round(pnl, 2), round(pct, 3)


def open_trade(symbol: str, side: str, entry_price: float, sl_price: Optional[float],
               tp_price: Optional[float], notional_usd: float, timeframe: str = "",
               brain_state: str = "", consensus: float = 0.0, confidence: float = 0.0,
               note: str = "", source: str = "MANUAL") -> Dict:
    side = LONG if str(side).upper() == LONG else SHORT
    entry_price = float(entry_price)
    notional_usd = max(1.0, float(notional_usd))
    if sl_price is None:
        sl_price = entry_price * (0.99 if side == LONG else 1.01)
    if tp_price is None:
        tp_price = entry_price * (1.02 if side == LONG else 0.98)
    qty = notional_usd / entry_price
    tid = str(uuid.uuid4())
    now = int(time.time())
    with _lock:
        conn = _connect()
        conn.execute(
            """INSERT INTO paper_trades
               (id, symbol, timeframe, side, status, entry_price, sl_price, tp_price,
                qty, notional_usd, opened_at, brain_state, consensus, confidence, note, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, symbol, timeframe, side, "OPEN", entry_price, float(sl_price),
             float(tp_price), qty, notional_usd, now, brain_state, float(consensus),
             float(confidence), note, source),
        )
        conn.commit()
    return get_trade(tid)


def get_trade(tid: str) -> Optional[Dict]:
    with _lock:
        conn = _connect()
        r = conn.execute("SELECT * FROM paper_trades WHERE id=?", (tid,)).fetchone()
    return _row_to_dict(r) if r else None


def close_trade(tid: str, exit_price: float, reason: str = "MANUAL") -> Optional[Dict]:
    t = get_trade(tid)
    if not t or t["status"] != "OPEN":
        return t
    exit_price = float(exit_price)
    pnl, pct = _pnl(t["side"], t["entry_price"], exit_price, t["qty"])
    with _lock:
        conn = _connect()
        conn.execute(
            """UPDATE paper_trades SET status='CLOSED', closed_at=?, exit_price=?,
               exit_reason=?, pnl=?, pnl_pct=? WHERE id=?""",
            (int(time.time()), exit_price, reason, pnl, pct, tid),
        )
        conn.commit()
    return get_trade(tid)


def check_open_trades(price: Optional[float]) -> int:
    """Auto-close OPEN trades whose SL/TP is hit by the live price."""
    if price is None:
        return 0
    closed = 0
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT * FROM paper_trades WHERE status='OPEN'").fetchall()
    for r in rows:
        t = _row_to_dict(r)
        side, sl, tp = t["side"], t["sl_price"], t["tp_price"]
        hit = None
        if side == LONG:
            if sl is not None and price <= sl:
                hit = ("SL", sl)
            elif tp is not None and price >= tp:
                hit = ("TP", tp)
        else:
            if sl is not None and price >= sl:
                hit = ("SL", sl)
            elif tp is not None and price <= tp:
                hit = ("TP", tp)
        if hit:
            close_trade(t["id"], hit[1], hit[0])
            closed += 1
    return closed


def list_trades(status: Optional[str] = None, live_price: Optional[float] = None) -> List[Dict]:
    with _lock:
        conn = _connect()
        if status in ("OPEN", "CLOSED"):
            rows = conn.execute("SELECT * FROM paper_trades WHERE status=? ORDER BY opened_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM paper_trades ORDER BY opened_at DESC").fetchall()
    out = []
    for r in rows:
        t = _row_to_dict(r)
        if t["status"] == "OPEN" and live_price is not None:
            upnl, upct = _pnl(t["side"], t["entry_price"], float(live_price), t["qty"])
            t["unrealized_pnl"] = upnl
            t["unrealized_pnl_pct"] = upct
            t["mark_price"] = round(float(live_price), 2)
        out.append(t)
    return out


def stats() -> Dict:
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT * FROM paper_trades WHERE status='CLOSED'").fetchall()
        open_count = conn.execute("SELECT COUNT(*) c FROM paper_trades WHERE status='OPEN'").fetchone()["c"]
    closed = [_row_to_dict(r) for r in rows]
    wins = [t for t in closed if (t["pnl"] or 0) > 0]
    losses = [t for t in closed if (t["pnl"] or 0) <= 0]
    total_pnl = round(sum(t["pnl"] or 0 for t in closed), 2)
    total_pct = round(sum(t["pnl_pct"] or 0 for t in closed), 3)
    win_rate = round(len(wins) / len(closed) * 100.0, 1) if closed else 0.0
    best = max((t["pnl"] or 0 for t in closed), default=0.0)
    worst = min((t["pnl"] or 0 for t in closed), default=0.0)
    return {
        "total_trades": len(closed) + open_count,
        "open_trades": open_count,
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": win_rate,
        "total_realized_pnl": total_pnl,
        "total_realized_pnl_pct": total_pct,
        "best_trade": round(best, 2),
        "worst_trade": round(worst, 2),
    }
