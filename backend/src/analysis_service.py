"""Analysis orchestration: run the 10 agents + HTF regime + Brain."""
from typing import List, Dict
import numpy as np

from .config import SYMBOL, HTF_TIMEFRAMES, ANALYSIS_LOOKBACK, AGENT_WEIGHTS
from .contract import AgentResult
from .market_data import data_access as dao
from .brain import brain as brain_engine
from .brain.mtf import regime_from_agents

from . import structure, breakout, fibonacci, elliott_wave, volume
from . import momentum, support_resistance, trend, pattern, fair_value_gap

AGENT_REGISTRY = {
    "market_structure": structure.analyze,
    "breakout": breakout.analyze,
    "fibonacci": fibonacci.analyze,
    "elliott_wave": elliott_wave.analyze,
    "volume": volume.analyze,
    "momentum": momentum.analyze,
    "support_resistance": support_resistance.analyze,
    "trend": trend.analyze,
    "pattern": pattern.analyze,
    "fair_value_gap": fair_value_gap.analyze,
}

AGENT_ORDER = list(AGENT_REGISTRY.keys())


def _native(obj):
    """Recursively convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_native(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return _native(obj.tolist())
    return obj


def run_agents(candles: List[Dict], timeframe: str) -> List[AgentResult]:
    results = []
    for aid in AGENT_ORDER:
        try:
            res = AGENT_REGISTRY[aid](candles, timeframe)
        except Exception as e:
            from .contract import neutral
            res = neutral(aid, timeframe, f"error: {e}", valid=False)
        results.append(res)
    return results


def _htf_regime() -> Dict:
    agents_by_tf = {}
    for tf in HTF_TIMEFRAMES:
        candles = dao.read_candles(tf, limit=ANALYSIS_LOOKBACK)
        if len(candles) < 60:
            continue
        agents_by_tf[tf] = run_agents(candles, tf)
    if not agents_by_tf:
        return {"regime": "NEUTRAL", "regime_score": 0.0, "per_timeframe": {}}
    return regime_from_agents(agents_by_tf)


def full_analysis(timeframe: str) -> Dict:
    candles = dao.read_candles(timeframe, limit=ANALYSIS_LOOKBACK)
    if len(candles) < 30:
        return {"error": "insufficient_data", "timeframe": timeframe,
                "candles": len(candles)}
    price = float(candles[-1]["close"])
    agents = run_agents(candles, timeframe)
    htf = _htf_regime()
    brain = brain_engine.decide(agents, price, timeframe, htf)
    return _native({
        "symbol": SYMBOL,
        "timeframe": timeframe,
        "price": price,
        "candle_count": len(candles),
        "agents": [a.to_dict() for a in agents],
        "agent_weights": AGENT_WEIGHTS,
        "htf_regime": htf,
        "brain": brain,
    })


def single_agent(agent_id: str, timeframe: str) -> Dict:
    if agent_id not in AGENT_REGISTRY:
        return {"error": "unknown_agent"}
    candles = dao.read_candles(timeframe, limit=ANALYSIS_LOOKBACK)
    if len(candles) < 30:
        return {"error": "insufficient_data"}
    return _native(AGENT_REGISTRY[agent_id](candles, timeframe).to_dict())
