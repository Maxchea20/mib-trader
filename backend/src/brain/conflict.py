"""PHASE E — Conflict / severe contradiction detection.

The Brain explicitly detects opposing evidence rather than using majority
voting. Strong two-sided disagreement reduces directional confidence and may
force WAIT or AVOID.
"""
from typing import List, Dict
from .. import settings
from ..contract import LONG, SHORT


def detect_conflict(agents: List, bias: str) -> Dict:
    CONFLICT = settings.conflict()
    AGENT_WEIGHTS = settings.weights()
    long_w = 0.0
    short_w = 0.0
    strong_long = []
    strong_short = []
    for res in agents:
        if not res.valid:
            continue
        w = AGENT_WEIGHTS.get(res.agent, 1.0) * res.confidence
        if res.direction == LONG:
            long_w += w
            if res.confidence >= CONFLICT["strong_confidence"]:
                strong_long.append(res.agent)
        elif res.direction == SHORT:
            short_w += w
            if res.confidence >= CONFLICT["strong_confidence"]:
                strong_short.append(res.agent)

    total = long_w + short_w
    if total <= 0:
        return {"conflict": False, "severity": "none", "opposing_ratio": 0.0,
                "opposing_agents": [], "penalty": 0.0, "veto": False}

    if bias == LONG:
        opposing = short_w
        opposing_strong = strong_short
    elif bias == SHORT:
        opposing = long_w
        opposing_strong = strong_long
    else:
        opposing = min(long_w, short_w)
        opposing_strong = strong_short if long_w >= short_w else strong_long

    ratio = opposing / total
    n_strong = len(opposing_strong)

    veto = ratio >= CONFLICT["veto_ratio"]
    severe = ratio >= CONFLICT["severe_ratio"]
    contradiction = (n_strong >= CONFLICT["contradiction_min_agents"]) or severe

    severity = "none"
    penalty = 0.0
    if veto:
        severity = "veto"
        penalty = CONFLICT["confidence_penalty"] * 2
    elif severe:
        severity = "severe"
        penalty = CONFLICT["confidence_penalty"] * 1.5
    elif contradiction:
        severity = "moderate"
        penalty = CONFLICT["confidence_penalty"]

    return {
        "conflict": contradiction or severe or veto,
        "severity": severity,
        "opposing_ratio": round(ratio, 3),
        "opposing_agents": opposing_strong,
        "penalty": round(penalty, 1),
        "veto": veto,
    }
