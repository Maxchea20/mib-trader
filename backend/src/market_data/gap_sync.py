"""Gap detection & historical gap recovery for persisted candles."""
from typing import List, Dict

from . import database as db
from . import mexc_market_data as mexc
from ..config import TF_SECONDS


def detect_gaps(symbol: str, timeframe: str) -> List[Dict]:
    """Return missing candle ranges based on expected interval spacing."""
    candles = db.get_candles(symbol, timeframe, limit=db.count_candles(symbol, timeframe) or 1)
    step = TF_SECONDS[timeframe]
    gaps = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]["ts"]
        cur = candles[i]["ts"]
        delta = cur - prev
        if delta > step * 1.5:
            missing = int(round(delta / step)) - 1
            gaps.append({"from_ts": prev, "to_ts": cur, "missing": missing})
    return gaps


async def sync_timeframe(symbol: str, timeframe: str, limit: int = 1000) -> Dict:
    """Fetch recent candles from MEXC REST and persist. Fills gaps because MEXC
    returns a contiguous window. Falls back gracefully on failure."""
    import time
    try:
        candles = await mexc.get_klines(symbol, timeframe, limit=limit)
        if not candles:
            db.set_sync_meta(symbol, timeframe, int(time.time()), "empty")
            return {"timeframe": timeframe, "status": "empty", "saved": 0}
        saved = db.upsert_candles(symbol, timeframe, candles)
        db.set_sync_meta(symbol, timeframe, int(time.time()), "ok")
        return {"timeframe": timeframe, "status": "ok", "saved": saved,
                "gaps": len(detect_gaps(symbol, timeframe))}
    except Exception as e:
        db.set_sync_meta(symbol, timeframe, int(time.time()), f"error")
        return {"timeframe": timeframe, "status": "error", "error": str(e), "saved": 0}


async def sync_latest(symbol: str, timeframe: str) -> Dict:
    """Latest-candle synchronization — small window for live forming candle."""
    import time
    try:
        candles = await mexc.get_klines(symbol, timeframe, limit=5)
        saved = db.upsert_candles(symbol, timeframe, candles)
        db.set_sync_meta(symbol, timeframe, int(time.time()), "ok")
        return {"timeframe": timeframe, "status": "ok", "saved": saved}
    except Exception as e:
        return {"timeframe": timeframe, "status": "error", "error": str(e)}
