"""MEXC Futures market-data client (REST + ticker + latest candle sync).

Live price/current forming candle uses the ticker + latest kline. Historical
candles come from the REST kline endpoint. If MEXC is unreachable (e.g. region
block), the caller falls back to seeded/simulated candles so the app still runs.
"""
import time
import httpx
from typing import List, Dict, Optional

from ..config import TF_MEXC, TF_SECONDS

BASE = "https://contract.mexc.com/api/v1/contract"


class MexcError(Exception):
    pass


async def ping() -> bool:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{BASE}/ping")
            return r.json().get("success", False)
    except Exception:
        return False


async def get_ticker(symbol: str) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{BASE}/ticker", params={"symbol": symbol})
            data = r.json()
            if not data.get("success"):
                return None
            d = data["data"]
            return {
                "symbol": d["symbol"],
                "last": float(d["lastPrice"]),
                "bid": float(d.get("bid1", d["lastPrice"])),
                "ask": float(d.get("ask1", d["lastPrice"])),
                "high24": float(d.get("high24Price", 0)),
                "low24": float(d.get("lower24Price", 0)),
                "volume24": float(d.get("volume24", 0)),
                "amount24": float(d.get("amount24", 0)),
                "change_rate": float(d.get("riseFallRate", 0)),
                "change_value": float(d.get("riseFallValue", 0)),
                "funding_rate": float(d.get("fundingRate", 0)),
                "index_price": float(d.get("indexPrice", d["lastPrice"])),
                "ts": int(d.get("timestamp", int(time.time() * 1000))),
            }
    except Exception as e:
        raise MexcError(str(e))


def _parse_kline(data: Dict) -> List[Dict]:
    t = data.get("time", [])
    o = data.get("open", [])
    c = data.get("close", [])
    h = data.get("high", [])
    low = data.get("low", [])
    vol = data.get("vol", data.get("volume", []))
    out = []
    for i in range(len(t)):
        try:
            out.append({
                "ts": int(t[i]),
                "open": float(o[i]),
                "high": float(h[i]),
                "low": float(low[i]),
                "close": float(c[i]),
                "volume": float(vol[i]) if i < len(vol) else 0.0,
            })
        except (IndexError, ValueError, TypeError):
            continue
    out.sort(key=lambda x: x["ts"])
    return out


async def get_klines(symbol: str, timeframe: str, limit: int = 1000,
                     start: Optional[int] = None, end: Optional[int] = None) -> List[Dict]:
    interval = TF_MEXC[timeframe]
    step = TF_SECONDS[timeframe]
    if end is None:
        end = int(time.time())
    if start is None:
        start = end - step * (limit + 2)
    params = {"interval": interval, "start": start, "end": end}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{BASE}/kline/{symbol}", params=params)
            data = r.json()
            if not data.get("success"):
                raise MexcError(f"kline not success: {data.get('code')}")
            return _parse_kline(data["data"])
    except MexcError:
        raise
    except Exception as e:
        raise MexcError(str(e))
