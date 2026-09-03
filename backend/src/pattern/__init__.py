"""AGENT 9 — PATTERN ANALYSIS.
Identifies structured chart patterns. Output includes direction, quality,
completion and confidence.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, find_pivots

AGENT_ID = "pattern"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 40:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    piv = find_pivots(a["high"], a["low"], left=3, right=3)
    if len(piv) < 4:
        return neutral(AGENT_ID, timeframe, "Too few pivots")
    close = float(a["close"][-1])

    highs = [p for p in piv if p["type"] == "H"][-3:]
    lows = [p for p in piv if p["type"] == "L"][-3:]

    pattern = None
    direction = NEUTRAL
    quality = 0.0
    completion = 0.0
    evidence = []

    def close_pct(x, y):
        return abs(x - y) / max(y, 1e-9) * 100

    # Double top / bottom
    if len(highs) >= 2 and close_pct(highs[-1]["price"], highs[-2]["price"]) < 0.4:
        pattern = "Double Top"
        direction = SHORT
        quality, completion = 0.7, 0.8
        evidence.append(f"Double top near {highs[-1]['price']:.1f}")
    elif len(lows) >= 2 and close_pct(lows[-1]["price"], lows[-2]["price"]) < 0.4:
        pattern = "Double Bottom"
        direction = LONG
        quality, completion = 0.7, 0.8
        evidence.append(f"Double bottom near {lows[-1]['price']:.1f}")
    elif len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1]["price"] > highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]
        if hl and lh:
            pattern = "Symmetrical Triangle (contracting)"
            direction = NEUTRAL
            quality, completion = 0.5, 0.5
            evidence.append("Converging highs and lows")
        elif hh and hl:
            pattern = "Ascending / Bull Flag"
            direction = LONG
            quality, completion = 0.6, 0.6
            evidence.append("Rising highs and lows")
        elif lh and ll:
            pattern = "Descending / Bear Flag"
            direction = SHORT
            quality, completion = 0.6, 0.6
            evidence.append("Falling highs and lows")

    if pattern is None:
        return neutral(AGENT_ID, timeframe, "No clear pattern", valid=True)

    evidence.append(f"Pattern: {pattern} | quality={quality:.0%} | completion={completion:.0%}")
    confidence = clamp(35 + quality * 45 + completion * 15, 0, 90)
    strength = clamp(quality * 70 + completion * 25, 0, 100)
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       [], timeframe, valid=True)
