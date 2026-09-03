"""PHASE D — Confluence / correlation deduplication.

Multiple agents pointing at the same price zone are correlated evidence. They
must not become fully independent votes. We cluster their key levels near the
current price and award a bonus with diminishing returns.
"""
from typing import List, Dict
from .. import settings
from ..indicators import cluster_levels


def find_confluence_zones(agents: List, price: float) -> List[Dict]:
    CONFLUENCE = settings.confluence()
    tol = CONFLUENCE["zone_tolerance_pct"]
    contributions = []  # (price, agent, direction, label)
    for res in agents:
        if res.agent not in CONFLUENCE["level_agents"]:
            continue
        for lv in res.key_levels:
            p = lv.get("price")
            if p is None:
                continue
            # only levels reasonably near current price matter for confluence
            if abs(p - price) / price * 100 <= 3.0:
                contributions.append({"price": p, "agent": res.agent,
                                       "direction": res.direction, "label": lv.get("label", "")})
    if not contributions:
        return []

    prices = [c["price"] for c in contributions]
    zones = cluster_levels(prices, tol)
    result = []
    for z in zones:
        members = [c for c in contributions
                   if z["low"] <= c["price"] <= z["high"] or abs(c["price"] - z["price"]) / z["price"] * 100 <= tol]
        agent_set = sorted(set(c["agent"] for c in members))
        if len(agent_set) >= 2:
            # diminishing-returns bonus
            df = CONFLUENCE["diminishing_factor"]
            bonus = 0.0
            for k in range(len(agent_set)):
                bonus += (df ** k) * 4.0
            bonus = min(bonus, CONFLUENCE["max_zone_bonus"])
            result.append({
                "price": z["price"],
                "low": z["low"],
                "high": z["high"],
                "agents": agent_set,
                "count": len(agent_set),
                "bonus": round(bonus, 1),
                "side": "support" if z["price"] <= price else "resistance",
            })
    result.sort(key=lambda r: r["count"], reverse=True)
    return result
