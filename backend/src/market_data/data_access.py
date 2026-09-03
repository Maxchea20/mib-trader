"""Read-only data access layer for the analysis agents.

Agents MUST read market history through this layer only. It never mutates data
and knows nothing about analysis logic.
"""
from typing import List, Dict

from . import database as db
from ..config import SYMBOL, TIMEFRAMES, TF_SECONDS


def read_candles(timeframe: str, limit: int = 1000, symbol: str = SYMBOL) -> List[Dict]:
    return db.get_candles(symbol, timeframe, limit=limit)


def read_sync_status(symbol: str = SYMBOL) -> Dict:
    out = {}
    for tf in TIMEFRAMES:
        cnt = db.count_candles(symbol, tf)
        mn, mx = db.bounds(symbol, tf)
        meta = db.get_sync_meta(symbol, tf)
        out[tf] = {
            "count": cnt,
            "first_ts": mn,
            "last_ts": mx,
            "last_sync": meta.get("last_sync"),
            "status": meta.get("last_status"),
        }
    return {"symbol": symbol, "db_path": db.db_path(), "timeframes": out}


def has_data(timeframe: str, symbol: str = SYMBOL) -> bool:
    return db.count_candles(symbol, timeframe) > 0
