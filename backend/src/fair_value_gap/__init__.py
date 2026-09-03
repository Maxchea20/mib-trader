"""AGENT 10 — FAIR VALUE GAP (ICT imbalance).
Detects 3-candle imbalances, their direction, price zone, relevance and status
(mitigated / unmitigated).
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays

AGENT_ID = "fair_value_gap"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 20:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    close = float(a["close"][-1])
    n = len(candles)
    fvgs = []
    # 3-candle FVG: bullish when low[i] > high[i-2]; bearish when high[i] < low[i-2]
    for i in range(2, n):
        h2 = a["high"][i - 2]
        l2 = a["low"][i - 2]
        li = a["low"][i]
        hi = a["high"][i]
        if li > h2:  # bullish gap between h2 and li
            zone_lo, zone_hi = float(h2), float(li)
            mitigated = float(np.min(a["low"][i + 1:])) <= zone_hi if i + 1 < n else False
            fvgs.append({"dir": "bull", "lo": zone_lo, "hi": zone_hi, "i": i,
                         "size": (zone_hi - zone_lo) / close * 100, "mitigated": mitigated})
        elif hi < l2:  # bearish gap between hi and l2
            zone_lo, zone_hi = float(hi), float(l2)
            mitigated = float(np.max(a["high"][i + 1:])) >= zone_lo if i + 1 < n else False
            fvgs.append({"dir": "bear", "lo": zone_lo, "hi": zone_hi, "i": i,
                         "size": (zone_hi - zone_lo) / close * 100, "mitigated": mitigated})

    # keep meaningful, recent, unmitigated gaps
    meaningful = [f for f in fvgs if f["size"] >= 0.05][-12:]
    unmit = [f for f in meaningful if not f["mitigated"]]
    if not meaningful:
        return neutral(AGENT_ID, timeframe, "No meaningful FVGs", valid=True)

    # nearest unmitigated FVG drives direction
    pool = unmit if unmit else meaningful
    nearest = min(pool, key=lambda f: abs((f["lo"] + f["hi"]) / 2 - close))
    mid = (nearest["lo"] + nearest["hi"]) / 2
    evidence = [f"{len(meaningful)} FVGs ({len(unmit)} unmitigated)"]

    if nearest["dir"] == "bull":
        direction = LONG
        evidence.append(f"Nearest bullish FVG {nearest['lo']:.1f}–{nearest['hi']:.1f} (support/demand)")
    else:
        direction = SHORT
        evidence.append(f"Nearest bearish FVG {nearest['lo']:.1f}–{nearest['hi']:.1f} (supply)")
    evidence.append("Unmitigated" if not nearest["mitigated"] else "Partially mitigated")

    dist = abs(mid - close) / close * 100
    confidence = clamp(65 - dist * 12 + nearest["size"] * 10, 30, 85)
    strength = clamp(55 - dist * 10 + nearest["size"] * 12, 10, 85)
    key_levels = []
    for f in pool[-4:]:
        key_levels.append({"label": f"FVG {'bull' if f['dir']=='bull' else 'bear'}",
                           "price": round((f["lo"] + f["hi"]) / 2, 2),
                           "low": round(f["lo"], 2), "high": round(f["hi"], 2),
                           "type": "fvg_bullish" if f["dir"] == "bull" else "fvg_bearish",
                           "mitigated": f["mitigated"]})
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       key_levels, timeframe, valid=True)
