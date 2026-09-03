"""PHASE C — HTF / LTF reconciliation.

HTF (4h/1d) determines the market regime/context. It is NOT averaged into the
same numerical score as LTF signals. Instead it acts as a gate: an opposing HTF
regime raises the confirmation requirements for a counter-trend LTF trade.
"""
from typing import List, Dict
from .. import settings
from ..contract import LONG, SHORT, NEUTRAL


def regime_from_agents(agents_by_tf: Dict[str, List]) -> Dict:
    """Compute HTF regime from agent outputs on 4h and 1d."""
    HTF_GATE = settings.htf_gate()
    AGENT_WEIGHTS = settings.weights()
    tf_scores = {}
    for tf, agents in agents_by_tf.items():
        num = 0.0
        den = 0.0
        for res in agents:
            if not res.valid:
                continue
            w = AGENT_WEIGHTS.get(res.agent, 1.0)
            num += res.sign() * res.confidence * w
            den += w
        score = num / den if den else 0.0
        tf_scores[tf] = round(score, 1)

    # weight 1d slightly higher than 4h for the regime
    weights = {"4h": 1.0, "1d": 1.3}
    num = sum(tf_scores.get(tf, 0) * weights.get(tf, 1) for tf in tf_scores)
    den = sum(weights.get(tf, 1) for tf in tf_scores)
    regime_score = num / den if den else 0.0

    if regime_score >= HTF_GATE["regime_min_score"]:
        regime = LONG
    elif regime_score <= -HTF_GATE["regime_min_score"]:
        regime = SHORT
    else:
        regime = NEUTRAL

    return {
        "regime": regime,
        "regime_score": round(regime_score, 1),
        "per_timeframe": tf_scores,
    }


def apply_gate(ltf_bias: str, regime: str) -> Dict:
    """Return the extra requirements imposed by the HTF gate on an LTF trade."""
    HTF_GATE = settings.htf_gate()
    extra_score = 0.0
    extra_conf = 0.0
    relation = "neutral"
    if regime == NEUTRAL or ltf_bias == NEUTRAL:
        relation = "neutral"
    elif ltf_bias == regime:
        relation = "aligned"
        extra_score = -HTF_GATE["aligned_bonus"]   # lower the bar
        extra_conf = -HTF_GATE["aligned_bonus"]
    else:
        relation = "counter-trend"
        extra_score = HTF_GATE["counter_trend_penalty"]
        extra_conf = HTF_GATE["counter_trend_confidence_penalty"]
    return {
        "relation": relation,
        "extra_score_required": round(extra_score, 1),
        "extra_confidence_required": round(extra_conf, 1),
    }
