"""Hands-free auto-trader.

Evaluates the Brain (all 10 agents + HTF regime) on each new candle close of the
auto-trade timeframe and manages a single AUTO paper position:
  - Brain LONG/SHORT with no AUTO position open  -> open one
  - Brain flips to the opposite side             -> close current (FLIP) + open new
  - Brain same side                              -> hold
  - Brain WAIT/AVOID                             -> do nothing (let SL/TP manage)

SL/TP are derived from ATR of the auto timeframe. Simulated only.
"""
import time
from typing import Dict, Optional

from .config import SYMBOL, ANALYSIS_LOOKBACK
from .market_data import data_access as dao
from .indicators import arrays, atr
from . import analysis_service
from . import paper_trading

CONFIG = {
    "enabled": True,
    "timeframe": "15m",
    "notional_usd": 1000.0,
    "sl_atr_mult": 1.5,
    "tp_atr_mult": 2.5,
}

STATE = {
    "last_candle_ts": None,
    "last_state": None,
    "last_action": None,
    "last_reason": None,
    "last_eval_at": None,
}


def _open_auto() -> Optional[Dict]:
    for t in paper_trading.list_trades("OPEN"):
        if t.get("source") == "AUTO":
            return t
    return None


def status() -> Dict:
    return {"config": CONFIG, "state": STATE, "open_auto_trade": _open_auto()}


def update(payload: Dict) -> Dict:
    turned_on = False
    if "enabled" in payload:
        new_enabled = bool(payload["enabled"])
        turned_on = new_enabled and not CONFIG["enabled"]
        CONFIG["enabled"] = new_enabled
    if payload.get("timeframe"):
        CONFIG["timeframe"] = str(payload["timeframe"])
    for k in ("notional_usd", "sl_atr_mult", "tp_atr_mult"):
        if k in payload and payload[k] is not None:
            try:
                CONFIG[k] = float(payload[k])
            except (TypeError, ValueError):
                pass
    if turned_on:
        # act immediately when switched on
        try:
            from .market_data import manager
            evaluate(manager.STATE.get("last_price"), force=True)
        except Exception:
            pass
    return status()


def _open(side: str, price: float, tf: str, brain: Dict, candles) -> None:
    a = arrays(candles)
    _atr = atr(a["high"], a["low"], a["close"], 14)
    if _atr <= 0:
        _atr = price * 0.005
    if side == "LONG":
        sl = price - CONFIG["sl_atr_mult"] * _atr
        tp = price + CONFIG["tp_atr_mult"] * _atr
    else:
        sl = price + CONFIG["sl_atr_mult"] * _atr
        tp = price - CONFIG["tp_atr_mult"] * _atr
    paper_trading.open_trade(
        symbol=SYMBOL, side=side, entry_price=price, sl_price=sl, tp_price=tp,
        notional_usd=CONFIG["notional_usd"], timeframe=tf,
        brain_state=brain.get("state", ""), consensus=brain.get("consensus_score", 0),
        confidence=brain.get("confidence", 0), note="auto-trade", source="AUTO",
    )


def evaluate(live_price: Optional[float], force: bool = False) -> Dict:
    if not CONFIG["enabled"]:
        STATE["last_action"] = "DISABLED"
        return STATE
    tf = CONFIG["timeframe"]
    candles = dao.read_candles(tf, limit=ANALYSIS_LOOKBACK)
    if len(candles) < 30:
        return STATE
    last_ts = candles[-1]["ts"]
    if not force and STATE["last_candle_ts"] == last_ts:
        return STATE  # only act on a new candle
    STATE["last_candle_ts"] = last_ts

    result = analysis_service.full_analysis(tf)
    brain = result.get("brain") or {}
    state = brain.get("state")
    price = live_price or result.get("price")
    STATE["last_state"] = state
    STATE["last_eval_at"] = int(time.time())

    open_auto = _open_auto()
    if state in ("LONG", "SHORT"):
        if open_auto is None:
            _open(state, price, tf, brain, candles)
            STATE["last_action"] = f"OPEN {state}"
            STATE["last_reason"] = f"Brain {state} @ consensus {brain.get('consensus_score')}"
        elif open_auto["side"] != state:
            paper_trading.close_trade(open_auto["id"], price, "FLIP")
            _open(state, price, tf, brain, candles)
            STATE["last_action"] = f"FLIP -> {state}"
            STATE["last_reason"] = f"Brain flipped to {state}"
        else:
            STATE["last_action"] = f"HOLD {state}"
            STATE["last_reason"] = "Signal unchanged"
    else:
        STATE["last_action"] = f"NO-TRADE ({state})"
        STATE["last_reason"] = f"Brain {state}"
    return STATE
