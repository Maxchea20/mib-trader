"""Live-first market-data manager: startup sync + background poller + fallback.

Startup behavior is LIVE-FIRST:
 1. Serve live price/current candle immediately (ticker).
 2. Load existing local SQLite candles immediately (chart renders from local).
 3. Run MEXC REST sync in the background.
 4. Detect + fill historical gaps, save back to SQLite.
"""
import asyncio
import time
import math
import random
from typing import Dict, Optional

from ..config import SYMBOL, TIMEFRAMES, TF_SECONDS, MAX_CANDLES
from . import database as db
from . import mexc_market_data as mexc
from . import gap_sync

STATE = {
    "connected": False,
    "source": "unknown",       # mexc | fallback
    "last_ticker": None,
    "last_price": None,
    "last_tick_ts": None,
    "startup_synced": False,
    "using_fallback": False,
}

_price_walk = None


def _seed_synthetic(symbol: str, timeframe: str, base_price: float, count: int = 600):
    """Seed deterministic-ish synthetic candles so the app runs if MEXC blocked."""
    step = TF_SECONDS[timeframe]
    now = int(time.time())
    start = now - step * count
    price = base_price
    candles = []
    rnd = random.Random(hash((symbol, timeframe)) & 0xFFFFFFFF)
    for i in range(count):
        ts = start + i * step
        drift = math.sin(i / 30.0) * base_price * 0.0008
        noise = (rnd.random() - 0.5) * base_price * 0.002
        o = price
        c = max(1.0, price + drift + noise)
        h = max(o, c) * (1 + rnd.random() * 0.0008)
        l = min(o, c) * (1 - rnd.random() * 0.0008)
        v = 1000 + rnd.random() * 4000
        candles.append({"ts": ts, "open": round(o, 1), "high": round(h, 1),
                        "low": round(l, 1), "close": round(c, 1), "volume": round(v, 1)})
        price = c
    db.upsert_candles(symbol, timeframe, candles)
    db.set_sync_meta(symbol, timeframe, now, "fallback")


async def initial_load():
    """Non-blocking: kick everything off. Returns immediately after DB init."""
    db.init_db()
    asyncio.create_task(_startup_sync())
    asyncio.create_task(_poll_loop())


async def _startup_sync():
    ok = await mexc.ping()
    STATE["connected"] = ok
    if ok:
        STATE["source"] = "mexc"
        for tf in TIMEFRAMES:
            r = await gap_sync.sync_timeframe(SYMBOL, tf, limit=MAX_CANDLES)
            await asyncio.sleep(0.15)
        STATE["startup_synced"] = True
    else:
        # fallback so the app still runs
        STATE["source"] = "fallback"
        STATE["using_fallback"] = True
        base = 60000.0
        for tf in TIMEFRAMES:
            if db.count_candles(SYMBOL, tf) < 60:
                _seed_synthetic(SYMBOL, tf, base)
        STATE["startup_synced"] = True


async def _poll_loop():
    """Live ticker + latest-candle sync loop."""
    full_sync_at = 0
    while True:
        try:
            t = await mexc.get_ticker(SYMBOL)
            if t:
                STATE["connected"] = True
                STATE["source"] = "mexc"
                STATE["using_fallback"] = False
                STATE["last_ticker"] = t
                STATE["last_price"] = t["last"]
                STATE["last_tick_ts"] = int(time.time())
                # keep latest candles fresh on the fast timeframes
                for tf in ["1m", "5m", "15m"]:
                    await gap_sync.sync_latest(SYMBOL, tf)
                # periodic full re-sync (gap recovery) every 5 min
                if time.time() - full_sync_at > 300:
                    for tf in TIMEFRAMES:
                        await gap_sync.sync_timeframe(SYMBOL, tf, limit=MAX_CANDLES)
                        await asyncio.sleep(0.1)
                    full_sync_at = time.time()
            else:
                STATE["connected"] = False
        except Exception:
            STATE["connected"] = False
            _fallback_tick()
        await asyncio.sleep(4)


def _fallback_tick():
    """Advance a synthetic price when MEXC is unreachable."""
    global _price_walk
    if _price_walk is None:
        _price_walk = STATE.get("last_price") or 60000.0
    _price_walk *= (1 + (random.random() - 0.5) * 0.0006)
    STATE["source"] = "fallback"
    STATE["using_fallback"] = True
    STATE["last_price"] = round(_price_walk, 1)
    STATE["last_tick_ts"] = int(time.time())
    STATE["last_ticker"] = {
        "symbol": SYMBOL, "last": STATE["last_price"], "bid": STATE["last_price"],
        "ask": STATE["last_price"], "high24": 0, "low24": 0, "volume24": 0,
        "amount24": 0, "change_rate": 0, "change_value": 0, "funding_rate": 0,
        "index_price": STATE["last_price"], "ts": int(time.time() * 1000),
    }


def live_status() -> Dict:
    age = None
    if STATE["last_tick_ts"]:
        age = int(time.time()) - STATE["last_tick_ts"]
    return {
        "connected": STATE["connected"],
        "source": STATE["source"],
        "using_fallback": STATE["using_fallback"],
        "startup_synced": STATE["startup_synced"],
        "last_price": STATE["last_price"],
        "tick_age_seconds": age,
        "ticker": STATE["last_ticker"],
    }
