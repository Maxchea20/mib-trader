"""AGENT 1 — MARKET STRUCTURE.
Detects HH/HL/LH/LL, Break of Structure (BOS) and Change of Character (CHoCH)
to determine structural direction.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, find_pivots

AGENT_ID = "market_structure"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 30:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    piv = find_pivots(a["high"], a["low"], left=3, right=3)
    highs = [p for p in piv if p["type"] == "H"]
    lows = [p for p in piv if p["type"] == "L"]
    if len(highs) < 2 or len(lows) < 2:
        return neutral(AGENT_ID, timeframe, "Insufficient swing points")

    last_highs = highs[-2:]
    last_lows = lows[-2:]
    hh = last_highs[-1]["price"] > last_highs[-2]["price"]
    hl = last_lows[-1]["price"] > last_lows[-2]["price"]
    lh = last_highs[-1]["price"] < last_highs[-2]["price"]
    ll = last_lows[-1]["price"] < last_lows[-2]["price"]

    evidence = []
    close = float(a["close"][-1])
    last_swing_high = last_highs[-1]["price"]
    last_swing_low = last_lows[-1]["price"]

    direction = NEUTRAL
    score = 0
    if hh and hl:
        direction, score = LONG, 2
        evidence.append("Higher High + Higher Low → bullish structure")
    elif lh and ll:
        direction, score = SHORT, 2
        evidence.append("Lower High + Lower Low → bearish structure")
    elif hh or hl:
        direction, score = LONG, 1
        evidence.append("Partial bullish structure")
    elif lh or ll:
        direction, score = SHORT, 1
        evidence.append("Partial bearish structure")

    # BOS: price closes beyond last swing high/low
    bos = None
    if close > last_swing_high:
        bos = "bullish"
        evidence.append(f"Bullish BOS: close broke swing high {last_swing_high:.1f}")
        if direction == SHORT:
            evidence.append("CHoCH: bearish→bullish shift")
            direction = LONG
        score += 1
    elif close < last_swing_low:
        bos = "bearish"
        evidence.append(f"Bearish BOS: close broke swing low {last_swing_low:.1f}")
        if direction == LONG:
            evidence.append("CHoCH: bullish→bearish shift")
            direction = SHORT
        score += 1

    confidence = clamp(45 + score * 13, 0, 95)
    strength = clamp(score * 22, 0, 100)
    if direction == NEUTRAL:
        confidence = 30
    key_levels = [
        {"label": "Swing High", "price": round(last_swing_high, 2), "type": "resistance"},
        {"label": "Swing Low", "price": round(last_swing_low, 2), "type": "support"},
    ]
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       key_levels, timeframe, valid=True)
