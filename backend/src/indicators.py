"""Shared technical-analysis math. Deterministic, numpy-based."""
import numpy as np
from typing import List, Dict, Tuple


def arrays(candles: List[Dict]) -> Dict[str, np.ndarray]:
    o = np.array([c["open"] for c in candles], dtype=float)
    h = np.array([c["high"] for c in candles], dtype=float)
    l = np.array([c["low"] for c in candles], dtype=float)
    cl = np.array([c["close"] for c in candles], dtype=float)
    v = np.array([c["volume"] for c in candles], dtype=float)
    t = np.array([c["ts"] for c in candles], dtype=float)
    return {"open": o, "high": h, "low": l, "close": cl, "volume": v, "ts": t}


def ema(values: np.ndarray, period: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values
    alpha = 2.0 / (period + 1.0)
    out = np.empty_like(values)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def sma(values: np.ndarray, period: int) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) < period:
        return float(np.mean(values)) if len(values) else 0.0
    return float(np.mean(values[-period:]))


def rsi(closes: np.ndarray, period: int = 14) -> float:
    closes = np.asarray(closes, dtype=float)
    if len(closes) < period + 1:
        return 50.0
    delta = np.diff(closes)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow + signal:
        return 0.0, 0.0, 0.0
    macd_line = ema(closes, fast) - ema(closes, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return float(macd_line[-1]), float(signal_line[-1]), float(hist[-1])


def roc(closes: np.ndarray, period: int = 12) -> float:
    if len(closes) < period + 1 or closes[-period - 1] == 0:
        return 0.0
    return float((closes[-1] - closes[-period - 1]) / closes[-period - 1] * 100.0)


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
    n = len(close)
    if n < 2:
        return 0.0
    prev_close = close[:-1]
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - prev_close),
                               np.abs(low[1:] - prev_close)))
    if len(tr) < period:
        return float(np.mean(tr)) if len(tr) else 0.0
    return float(np.mean(tr[-period:]))


def rvol(volume: np.ndarray, period: int = 20) -> float:
    if len(volume) < 2:
        return 1.0
    base = volume[-period - 1:-1] if len(volume) > period else volume[:-1]
    avg = np.mean(base) if len(base) else 0.0
    if avg <= 0:
        return 1.0
    return float(volume[-1] / avg)


def find_pivots(high: np.ndarray, low: np.ndarray, left: int = 3, right: int = 3):
    """Return list of pivots: {'i', 'price', 'type'} where type in {'H','L'} asc by index."""
    piv = []
    n = len(high)
    for i in range(left, n - right):
        wl, wr = slice(i - left, i), slice(i + 1, i + 1 + right)
        if high[i] >= np.max(high[wl]) and high[i] >= np.max(high[wr]):
            piv.append({"i": i, "price": float(high[i]), "type": "H"})
        if low[i] <= np.min(low[wl]) and low[i] <= np.min(low[wr]):
            piv.append({"i": i, "price": float(low[i]), "type": "L"})
    piv.sort(key=lambda p: p["i"])
    return piv


def cluster_levels(prices: List[float], tolerance_pct: float) -> List[Dict]:
    """Cluster nearby prices into zones. Returns [{price, count, low, high}]."""
    if not prices:
        return []
    prices = sorted(prices)
    zones = []
    cur = [prices[0]]
    for p in prices[1:]:
        if abs(p - cur[-1]) / max(cur[-1], 1e-9) * 100.0 <= tolerance_pct:
            cur.append(p)
        else:
            zones.append(cur)
            cur = [p]
    zones.append(cur)
    out = []
    for z in zones:
        out.append({
            "price": round(float(np.mean(z)), 2),
            "count": len(z),
            "low": round(float(min(z)), 2),
            "high": round(float(max(z)), 2),
        })
    return out
