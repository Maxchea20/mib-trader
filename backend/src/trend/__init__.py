"""AGENT 8 — TREND.
Determines the broader regime using an EMA ribbon, EMA slope and structure.
(Multi-timeframe reconciliation is handled by the Brain via HTF regime.)
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, ema

AGENT_ID = "trend"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 60:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    closes = a["close"]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    e100 = ema(closes, 100) if len(closes) >= 100 else ema(closes, min(80, len(closes) - 1))
    close = float(closes[-1])

    stacked_up = e20[-1] > e50[-1] > e100[-1]
    stacked_dn = e20[-1] < e50[-1] < e100[-1]
    slope20 = (e20[-1] - e20[-10]) / max(abs(e20[-10]), 1e-9) * 100 if len(e20) >= 10 else 0

    evidence = [
        f"EMA20={e20[-1]:.1f}, EMA50={e50[-1]:.1f}, EMA100={e100[-1]:.1f}",
        f"EMA20 slope={slope20:+.2f}%",
    ]
    score = 0
    direction = NEUTRAL
    if stacked_up:
        direction, score = LONG, 2
        evidence.append("Bullish EMA ribbon (20>50>100)")
    elif stacked_dn:
        direction, score = SHORT, 2
        evidence.append("Bearish EMA ribbon (20<50<100)")
    elif close > e50[-1]:
        direction, score = LONG, 1
        evidence.append("Price above EMA50")
    elif close < e50[-1]:
        direction, score = SHORT, 1
        evidence.append("Price below EMA50")

    if direction == LONG and slope20 > 0:
        score += 1
    if direction == SHORT and slope20 < 0:
        score += 1

    confidence = clamp(40 + score * 15 + min(abs(slope20) * 6, 15), 0, 94)
    strength = clamp(score * 25 + min(abs(slope20) * 8, 20), 0, 100)
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       [{"label": "EMA50", "price": round(float(e50[-1]), 2), "type": "dynamic"}],
                       timeframe, valid=True)
