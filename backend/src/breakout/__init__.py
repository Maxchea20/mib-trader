"""AGENT 2 — BREAKOUT / BREAKDOWN.
Distinguishes genuine breakouts from fakeouts using range, volume, ATR and
follow-through.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, atr, rvol

AGENT_ID = "breakout"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 40:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    lookback = 20
    recent_high = float(np.max(a["high"][-lookback - 1:-1]))
    recent_low = float(np.min(a["low"][-lookback - 1:-1]))
    close = float(a["close"][-1])
    _atr = atr(a["high"], a["low"], a["close"], 14)
    _rvol = rvol(a["volume"], 20)
    evidence = []

    direction = NEUTRAL
    quality = 0.0
    broke_up = close > recent_high
    broke_dn = close < recent_low
    if broke_up:
        direction = LONG
        margin = (close - recent_high) / max(_atr, 1e-9)
        evidence.append(f"Close broke {lookback}-bar range high {recent_high:.1f}")
    elif broke_dn:
        direction = SHORT
        margin = (recent_low - close) / max(_atr, 1e-9)
        evidence.append(f"Close broke {lookback}-bar range low {recent_low:.1f}")
    else:
        pos = (close - recent_low) / max(recent_high - recent_low, 1e-9)
        return AgentResult(AGENT_ID, NEUTRAL, clamp(30 + abs(pos - 0.5) * 20, 0, 60),
                           20, [f"Price inside range ({recent_low:.1f}–{recent_high:.1f})"],
                           [{"label": "Range High", "price": round(recent_high, 2), "type": "resistance"},
                            {"label": "Range Low", "price": round(recent_low, 2), "type": "support"}],
                           timeframe, valid=True)

    # Confirmations
    vol_ok = _rvol >= 1.3
    if vol_ok:
        evidence.append(f"Volume confirmation RVOL={_rvol:.2f}")
        quality += 1
    else:
        evidence.append(f"Weak volume RVOL={_rvol:.2f} → fake-out risk")
    if margin >= 0.5:
        evidence.append(f"Displacement {margin:.2f}×ATR beyond level")
        quality += 1
    # follow-through: last 2 closes in breakout direction
    if direction == LONG and a["close"][-1] > a["close"][-2] > a["close"][-3]:
        quality += 1
        evidence.append("Follow-through: 2 rising closes")
    if direction == SHORT and a["close"][-1] < a["close"][-2] < a["close"][-3]:
        quality += 1
        evidence.append("Follow-through: 2 falling closes")

    confidence = clamp(40 + quality * 15 + (10 if vol_ok else 0), 0, 95)
    strength = clamp(quality * 25, 0, 100)
    valid = vol_ok or margin >= 0.5
    if not valid:
        evidence.append("Marked low-reliability (unconfirmed breakout)")
    key_levels = [
        {"label": "Breakout Level", "price": round(recent_high if direction == LONG else recent_low, 2),
         "type": "breakout"},
    ]
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       key_levels, timeframe, valid=True)
