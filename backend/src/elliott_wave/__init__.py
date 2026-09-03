"""AGENT 4 — ELLIOTT WAVE.
Candidate wave counts with confidence. Subjective/soft input — must NOT be
treated as an absolute directional signal (low weight in the Brain).
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, find_pivots

AGENT_ID = "elliott_wave"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 40:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    piv = find_pivots(a["high"], a["low"], left=4, right=4)
    if len(piv) < 5:
        return neutral(AGENT_ID, timeframe, "Too few pivots for a wave count", valid=False)

    seq = piv[-6:]
    prices = [p["price"] for p in seq]
    # Direction of the overall recent leg
    net = prices[-1] - prices[0]
    swings = len(seq)
    evidence = [f"Detected {swings} recent swing pivots"]

    # Very rough heuristic: a clean 5-swing alternating structure suggests an
    # impulse in the net direction; 3 swings suggests a correction.
    directions = [1 if seq[i]["price"] > seq[i - 1]["price"] else -1 for i in range(1, len(seq))]
    alternating = all(directions[i] != directions[i + 1] for i in range(len(directions) - 1))

    if alternating and swings >= 5:
        wave = "Impulsive (motive 1-5) candidate"
        direction = LONG if net > 0 else SHORT
        confidence = 42
        evidence.append("Alternating swings resemble a 5-wave impulse")
    elif alternating:
        wave = "Corrective (A-B-C) candidate"
        direction = SHORT if net > 0 else LONG
        confidence = 34
        evidence.append("3-swing structure resembles an A-B-C correction")
    else:
        wave = "Unclear / overlapping"
        direction = NEUTRAL
        confidence = 22
        evidence.append("Overlapping swings — no clean count")

    evidence.append(f"Candidate: {wave}")
    evidence.append("Soft input — not a standalone directional signal")
    strength = clamp(confidence * 0.6, 0, 60)
    key_levels = [{"label": "Wave origin", "price": round(prices[0], 2), "type": "structure"},
                  {"label": "Wave current", "price": round(prices[-1], 2), "type": "structure"}]
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       key_levels, timeframe, valid=True)
