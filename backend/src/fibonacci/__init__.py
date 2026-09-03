"""AGENT 3 — FIBONACCI.
Retracement/extension levels from the last dominant swing.
For an upswing: Level = High - ((High - Low) × ratio).
Note: 50% is a conventional retracement level, not a true Fibonacci ratio.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, find_pivots

AGENT_ID = "fibonacci"
RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
EXT = [1.272, 1.618]


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 30:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    win = min(120, len(candles))
    hi_i = int(np.argmax(a["high"][-win:])) + (len(candles) - win)
    lo_i = int(np.argmin(a["low"][-win:])) + (len(candles) - win)
    high = float(a["high"][hi_i])
    low = float(a["low"][lo_i])
    close = float(a["close"][-1])
    rng = high - low
    if rng <= 0:
        return neutral(AGENT_ID, timeframe, "Flat range")

    upswing = lo_i < hi_i  # low happened before high → recent leg is up
    levels = []
    for r in RATIOS:
        # retracement level from the impulse
        price = high - rng * r if upswing else low + rng * r
        note = "50% (conventional, not a true Fib ratio)" if r == 0.5 else f"{int(r*100)}%"
        levels.append({"label": f"Fib {note}", "price": round(price, 2), "ratio": r,
                       "type": "fibonacci"})
    golden = high - rng * 0.618 if upswing else low + rng * 0.618

    # Where is price vs golden pocket?
    evidence = []
    direction = NEUTRAL
    if upswing:
        evidence.append(f"Upswing leg {low:.1f} → {high:.1f}")
        if close >= golden:
            direction = LONG
            evidence.append(f"Price above 0.618 golden pocket ({golden:.1f}) → retracement holding")
        else:
            direction = SHORT
            evidence.append(f"Price broke below 0.618 ({golden:.1f}) → deep retracement")
    else:
        evidence.append(f"Downswing leg {high:.1f} → {low:.1f}")
        if close <= golden:
            direction = SHORT
            evidence.append(f"Price below 0.618 golden pocket ({golden:.1f}) → retracement holding")
        else:
            direction = LONG
            evidence.append(f"Price above 0.618 ({golden:.1f}) → deep retracement")

    # distance to nearest fib level → confidence in reaction
    dists = [abs(close - lv["price"]) / close * 100 for lv in levels]
    nearest = min(dists)
    confidence = clamp(70 - nearest * 8, 30, 88)
    strength = clamp(60 - nearest * 6, 10, 90)
    ext_price = high + rng * (EXT[1] - 1) if upswing else low - rng * (EXT[1] - 1)
    levels.append({"label": "Fib Ext 1.618", "price": round(ext_price, 2), "ratio": 1.618, "type": "fibonacci"})
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       levels, timeframe, valid=True)
