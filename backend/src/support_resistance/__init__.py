"""AGENT 7 — SUPPORT / RESISTANCE.
Clusters pivot levels into zones rather than treating each price independently.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, neutral, clamp
from ..indicators import arrays, find_pivots, cluster_levels

AGENT_ID = "support_resistance"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 40:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    close = float(a["close"][-1])
    piv = find_pivots(a["high"], a["low"], left=3, right=3)
    if len(piv) < 4:
        return neutral(AGENT_ID, timeframe, "Too few pivots")

    prices = [p["price"] for p in piv]
    tol = 0.4
    zones = cluster_levels(prices, tol)
    # rank by number of touches
    zones.sort(key=lambda z: z["count"], reverse=True)

    supports = sorted([z for z in zones if z["price"] < close], key=lambda z: -z["price"])
    resistances = sorted([z for z in zones if z["price"] >= close], key=lambda z: z["price"])

    key_levels = []
    for z in supports[:3]:
        key_levels.append({"label": f"Support ({z['count']}x)", "price": z["price"],
                           "type": "support", "touches": z["count"]})
    for z in resistances[:3]:
        key_levels.append({"label": f"Resistance ({z['count']}x)", "price": z["price"],
                           "type": "resistance", "touches": z["count"]})

    evidence = [f"{len(zones)} clustered level zones detected"]
    direction = NEUTRAL
    nearest_sup = supports[0]["price"] if supports else None
    nearest_res = resistances[0]["price"] if resistances else None
    dist_sup = (close - nearest_sup) / close * 100 if nearest_sup else 999
    dist_res = (nearest_res - close) / close * 100 if nearest_res else 999

    if dist_sup < dist_res and dist_sup < 0.6:
        direction = LONG
        evidence.append(f"Price near support {nearest_sup:.1f} → bounce zone")
    elif dist_res < dist_sup and dist_res < 0.6:
        direction = SHORT
        evidence.append(f"Price near resistance {nearest_res:.1f} → rejection zone")
    else:
        evidence.append("Price in mid-range between S/R")

    proximity = min(dist_sup, dist_res)
    confidence = clamp(70 - proximity * 22, 30, 88)
    strength = clamp(60 - proximity * 18, 10, 85)
    if direction == NEUTRAL:
        confidence = min(confidence, 45)
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       key_levels, timeframe, valid=True)
