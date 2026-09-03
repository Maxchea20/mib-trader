"""PHASE G — Brain implementation (final decision engine).

Consumes the standardized outputs of the 10 agents plus the HTF regime and
produces exactly one state: LONG / SHORT / WAIT / AVOID, with a traceable
reasoning chain. It uses weighted evidence — NOT vote counting.
"""
from typing import List, Dict
from ..config import CONFIG_VERSION, ASSUMPTIONS
from .. import settings
from ..contract import (LONG, SHORT, NEUTRAL, STATE_LONG, STATE_SHORT,
                        STATE_WAIT, STATE_AVOID, clamp)
from .confluence import find_confluence_zones
from .conflict import detect_conflict
from .mtf import apply_gate


def _base_consensus(agents: List) -> Dict:
    """Base Consensus Score = Σ(direction × confidence × weight) / Σ weights."""
    num = 0.0
    den = 0.0
    contributions = []
    active = 0
    AGENT_WEIGHTS = settings.weights()
    for res in agents:
        if not res.valid:
            continue
        active += 1
        w = AGENT_WEIGHTS.get(res.agent, 1.0)
        score = res.sign() * res.confidence * w
        num += score
        den += w
        contributions.append({
            "agent": res.agent, "direction": res.direction,
            "confidence": round(res.confidence, 1), "weight": w,
            "contribution": round(score, 1),
        })
    base = num / den if den else 0.0
    return {"base_consensus": round(base, 1), "active_agents": active,
            "sum_weights": round(den, 2), "contributions": contributions}


def decide(agents: List, price: float, timeframe: str, htf: Dict) -> Dict:
    AGENT_WEIGHTS = settings.weights()
    ENTRY = settings.entry()
    base = _base_consensus(agents)
    consensus = base["base_consensus"]

    # PHASE F — directional bias
    if consensus >= ENTRY["direction_min_score"]:
        bias = LONG
    elif consensus <= -ENTRY["direction_min_score"]:
        bias = SHORT
    else:
        bias = NEUTRAL

    # PHASE D — confluence (increases confidence with diminishing returns)
    zones = find_confluence_zones(agents, price)
    confluence_bonus = sum(z["bonus"] for z in zones[:3])

    # PHASE E — conflict
    conflict = detect_conflict(agents, bias)

    # base confidence from |consensus| + confluence − conflict penalty
    confidence = clamp(abs(consensus) + confluence_bonus - conflict["penalty"], 0, 100)

    # PHASE C — HTF gate
    regime = htf.get("regime", NEUTRAL)
    gate = apply_gate(bias, regime)
    entry_score_req = ENTRY["entry_min_score"] + gate["extra_score_required"]
    entry_conf_req = ENTRY["entry_min_confidence"] + gate["extra_confidence_required"]

    reasons = []
    # Build reasons from strongest aligned agents
    aligned = sorted([r for r in agents if r.valid and r.direction == bias and bias != NEUTRAL],
                     key=lambda r: r.confidence * AGENT_WEIGHTS.get(r.agent, 1), reverse=True)
    for r in aligned[:6]:
        head = r.evidence[0] if r.evidence else r.direction
        reasons.append(f"{_name(r.agent)}: {r.direction} {r.confidence:.0f}% — {head}")
    for z in zones[:2]:
        reasons.append(f"Confluence zone @ {z['price']:.1f} ({', '.join(_name(a) for a in z['agents'])}) +{z['bonus']}")
    reasons.append(f"HTF regime: {regime} ({htf.get('regime_score', 0):+.0f}) → {gate['relation']}")

    # PHASE F — final state resolution
    state, why = _resolve_state(
        bias, consensus, confidence, base["active_agents"], conflict, gate,
        entry_score_req, entry_conf_req, regime,
    )

    return {
        "state": state,
        "direction": bias,
        "consensus_score": consensus,
        "confidence": round(confidence, 1),
        "base_consensus": consensus,
        "confluence_bonus": round(confluence_bonus, 1),
        "confluence_zones": zones,
        "conflict": conflict,
        "htf_gate": gate,
        "htf_regime": htf,
        "entry_score_required": round(entry_score_req, 1),
        "entry_confidence_required": round(entry_conf_req, 1),
        "reasons": reasons,
        "why_state": why,
        "contributions": base["contributions"],
        "active_agents": base["active_agents"],
        "sum_weights": base["sum_weights"],
        "timeframe": timeframe,
        "config_version": CONFIG_VERSION,
        "assumptions": ASSUMPTIONS,
    }


def _resolve_state(bias, consensus, confidence, active, conflict, gate,
                   score_req, conf_req, regime):
    ENTRY = settings.entry()
    why = []
    # AVOID conditions (explicit vetoes / poor conditions)
    if active < ENTRY["min_valid_agents"]:
        why.append(f"Only {active} valid agents (min {ENTRY['min_valid_agents']}) — poor conditions")
        return STATE_AVOID, why
    if conflict["veto"]:
        why.append(f"Hard veto: opposing evidence ratio {conflict['opposing_ratio']:.0%}")
        return STATE_AVOID, why
    if conflict["severity"] == "severe":
        why.append(f"Severe two-sided conflict ({', '.join(conflict['opposing_agents'])})")
        return STATE_AVOID, why

    if bias == NEUTRAL:
        why.append(f"No directional bias (consensus {consensus:+.0f} within neutral band)")
        return STATE_WAIT, why

    mag = abs(consensus)
    ready = mag >= score_req and confidence >= conf_req
    if ready:
        why.append(f"Consensus {consensus:+.0f} ≥ required {score_req:.0f}")
        why.append(f"Confidence {confidence:.0f}% ≥ required {conf_req:.0f}%")
        if gate["relation"] == "aligned":
            why.append(f"Aligned with HTF regime ({regime})")
        return (STATE_LONG if bias == LONG else STATE_SHORT), why

    # bias exists but not ready → WAIT
    if mag < score_req:
        why.append(f"{bias} bias but consensus {consensus:+.0f} < required {score_req:.0f}")
    if confidence < conf_req:
        why.append(f"Confidence {confidence:.0f}% < required {conf_req:.0f}%")
    if gate["relation"] == "counter-trend":
        why.append(f"Counter-trend to HTF regime ({regime}) — higher bar applied")
    if conflict["severity"] == "moderate":
        why.append(f"Moderate conflict ({', '.join(conflict['opposing_agents'])}) reduced confidence")
    return STATE_WAIT, why


_NAMES = {
    "market_structure": "Structure", "breakout": "Breakout", "fibonacci": "Fibonacci",
    "elliott_wave": "Elliott Wave", "volume": "Volume", "momentum": "Momentum",
    "support_resistance": "Support/Resistance", "trend": "Trend",
    "pattern": "Pattern", "fair_value_gap": "FVG",
}


def _name(agent_id: str) -> str:
    return _NAMES.get(agent_id, agent_id)
