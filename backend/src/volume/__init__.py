"""AGENT 5 — VOLUME.
RVOL, volume expansion, volume confirmation and breakout volume quality.
Determines whether participation supports the directional move.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, rvol

AGENT_ID = "volume"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 25:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    _rvol = rvol(a["volume"], 20)
    evidence = [f"RVOL={_rvol:.2f}"]

    # Volume-weighted direction over last N candles: are up-candles heavier?
    n = 10
    up_vol = 0.0
    dn_vol = 0.0
    for i in range(len(candles) - n, len(candles)):
        if a["close"][i] >= a["open"][i]:
            up_vol += a["volume"][i]
        else:
            dn_vol += a["volume"][i]
    total = up_vol + dn_vol
    bias = (up_vol - dn_vol) / total if total > 0 else 0.0

    if bias > 0.15:
        direction = LONG
        evidence.append(f"Buy-side volume dominant ({up_vol/total*100:.0f}%)")
    elif bias < -0.15:
        direction = SHORT
        evidence.append(f"Sell-side volume dominant ({dn_vol/total*100:.0f}%)")
    else:
        direction = NEUTRAL
        evidence.append("Balanced participation")

    expansion = _rvol >= 1.4
    if expansion:
        evidence.append("Volume expansion — supports current move")
    elif _rvol < 0.7:
        evidence.append("Volume contraction — weak participation")

    confidence = clamp(35 + abs(bias) * 90 + (12 if expansion else 0), 0, 92)
    strength = clamp(abs(bias) * 120 + (_rvol - 1) * 20, 0, 100)
    if direction == NEUTRAL:
        confidence = min(confidence, 45)
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       [], timeframe, valid=True)
