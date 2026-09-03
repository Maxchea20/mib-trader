"""Backtesting — replay stored SQLite history through the Brain.

For each sampled historical candle we rebuild the exact agent + Brain decision
using only data available up to that point, then measure the forward return over
N candles. Results are HONEST and hypothetical: gross, no fees, no slippage,
no position sizing. This is analysis/decision-support, not a profitability claim.
"""
from typing import Dict, List
import numpy as np

from .config import ANALYSIS_LOOKBACK, HTF_TIMEFRAMES
from .market_data import data_access as dao
from . import analysis_service as svc
from .brain import brain as brain_engine
from .brain.mtf import regime_from_agents


def _htf_regime_at(ts: int, htf_candles: Dict[str, List], cache: Dict) -> Dict:
    agents_by_tf = {}
    subs = {}
    for tf, candles in htf_candles.items():
        sub = [c for c in candles if c["ts"] <= ts]
        subs[tf] = len(sub)
        if len(sub) >= 60:
            agents_by_tf[tf] = sub[-ANALYSIS_LOOKBACK:]
    key = tuple(sorted(subs.items()))
    if key in cache:
        return cache[key]
    if not agents_by_tf:
        res = {"regime": "NEUTRAL", "regime_score": 0.0, "per_timeframe": {}}
    else:
        by_tf = {tf: svc.run_agents(c, tf) for tf, c in agents_by_tf.items()}
        res = regime_from_agents(by_tf)
    cache[key] = res
    return res


def run_backtest(timeframe: str, lookback: int = 150, forward: int = 8, step: int = 3) -> Dict:
    lookback = max(20, min(int(lookback), 400))
    forward = max(1, min(int(forward), 48))
    step = max(1, min(int(step), 10))

    need = ANALYSIS_LOOKBACK + lookback + forward
    candles = dao.read_candles(timeframe, limit=need)
    if len(candles) < ANALYSIS_LOOKBACK + forward + 10:
        return {"error": "insufficient_data", "timeframe": timeframe,
                "have": len(candles), "need": need}

    htf_candles = {tf: dao.read_candles(tf, limit=ANALYSIS_LOOKBACK * 3) for tf in HTF_TIMEFRAMES}
    cache: Dict = {}

    n = len(candles)
    start = max(ANALYSIS_LOOKBACK, n - lookback - forward)
    end = n - forward

    points = []
    equity = 0.0
    curve = []
    state_counts = {"LONG": 0, "SHORT": 0, "WAIT": 0, "AVOID": 0}
    dir_returns = []  # signed returns for directional (LONG/SHORT) calls
    long_rets, short_rets = [], []

    for i in range(start, end, step):
        window = candles[max(0, i - ANALYSIS_LOOKBACK):i + 1]
        if len(window) < 30:
            continue
        price = float(window[-1]["close"])
        agents = svc.run_agents(window, timeframe)
        htf = _htf_regime_at(window[-1]["ts"], htf_candles, cache)
        decision = brain_engine.decide(agents, price, timeframe, htf)
        state = decision["state"]
        fwd = float(candles[i + forward]["close"])
        ret = (fwd - price) / price * 100.0
        state_counts[state] = state_counts.get(state, 0) + 1

        signed = None
        correct = None
        if state == "LONG":
            signed = ret
            correct = ret > 0
            long_rets.append(ret)
        elif state == "SHORT":
            signed = -ret
            correct = ret < 0
            short_rets.append(ret)

        if signed is not None:
            dir_returns.append(signed)
            equity += signed
            curve.append({"ts": int(window[-1]["ts"]), "equity": round(equity, 3)})

        points.append({
            "ts": int(window[-1]["ts"]),
            "price": round(price, 2),
            "state": state,
            "direction": decision["direction"],
            "consensus": decision["consensus_score"],
            "confidence": decision["confidence"],
            "forward_return_pct": round(ret, 3),
            "signed_return_pct": round(signed, 3) if signed is not None else None,
            "correct": correct,
        })

    dir_trades = len(dir_returns)
    wins = sum(1 for p in points if p["correct"] is True)
    win_rate = (wins / dir_trades * 100.0) if dir_trades else 0.0
    net = float(np.sum(dir_returns)) if dir_returns else 0.0
    avg_dir = float(np.mean(dir_returns)) if dir_returns else 0.0

    summary = {
        "timeframe": timeframe,
        "evaluations": len(points),
        "forward_candles": forward,
        "step": step,
        "state_counts": state_counts,
        "directional_trades": dir_trades,
        "wins": wins,
        "win_rate_pct": round(win_rate, 1),
        "net_return_pct": round(net, 2),
        "avg_return_per_trade_pct": round(avg_dir, 3),
        "avg_long_return_pct": round(float(np.mean(long_rets)), 3) if long_rets else 0.0,
        "avg_short_return_pct": round(float(np.mean(short_rets)), 3) if short_rets else 0.0,
        "disclaimer": ("Hypothetical, gross of fees/slippage. Each directional signal "
                       "is evaluated over a fixed forward window and does not represent "
                       "a live trading strategy or guaranteed results."),
    }
    return {"summary": summary, "equity_curve": curve, "points": points}
