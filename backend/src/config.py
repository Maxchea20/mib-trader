"""
MIB-Trader — Version 1 configurable assumptions.

IMPORTANT: The blueprint deliberately leaves several formulas and thresholds
undecided. They are exposed here as clearly-labelled V1 parameters. None of
these values are scientifically proven — they are starting points for
calibration / backtesting.
"""

CONFIG_VERSION = "v1"

# --- Market data ---------------------------------------------------------
SYMBOL = "BTC_USDT"

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

# Map our timeframe labels -> MEXC contract kline interval + seconds/candle.
TF_MEXC = {
    "1m": "Min1", "5m": "Min5", "15m": "Min15", "30m": "Min30",
    "1h": "Min60", "4h": "Hour4", "1d": "Day1",
}
TF_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400,
}

# Which timeframes are Higher-Time-Frame (regime/context) vs Lower (execution).
HTF_TIMEFRAMES = ["4h", "1d"]
LTF_TIMEFRAMES = ["1m", "5m", "15m", "30m"]

# How many candles to keep/analyze per request.
MAX_CANDLES = 1000
ANALYSIS_LOOKBACK = 320

# --- PHASE B: Agent weights (V1 assumptions) -----------------------------
# Higher weight == more influence on the base consensus score.
AGENT_WEIGHTS = {
    "market_structure": 1.4,
    "trend": 1.3,
    "breakout": 1.1,
    "momentum": 1.2,
    "volume": 1.0,
    "support_resistance": 1.1,
    "fibonacci": 0.8,
    "fair_value_gap": 0.9,
    "pattern": 0.8,
    "elliott_wave": 0.5,   # subjective/soft input — intentionally low weight
}

# --- PHASE C: HTF gate rules (V1 assumptions) ----------------------------
# An opposing HTF regime does not make a trade impossible, it raises the bar.
HTF_GATE = {
    # regime is decided if HTF directional score magnitude exceeds this
    "regime_min_score": 20.0,
    # extra consensus points required when LTF trades AGAINST the HTF regime
    "counter_trend_penalty": 25.0,
    # extra confidence points required when trading against HTF regime
    "counter_trend_confidence_penalty": 12.0,
    # bonus (lowered requirement) when LTF aligns with HTF regime
    "aligned_bonus": 8.0,
}

# --- PHASE D: Confluence / correlation (V1 assumptions) ------------------
CONFLUENCE = {
    # two levels are in the same zone if within this % of price
    "zone_tolerance_pct": 0.35,
    # each additional correlated confirmation in a zone is worth this fraction
    # of the previous one (diminishing returns)
    "diminishing_factor": 0.5,
    # max confidence bonus a single confluence zone can add
    "max_zone_bonus": 12.0,
    # agents whose key levels participate in confluence clustering
    "level_agents": ["fibonacci", "support_resistance", "fair_value_gap", "breakout"],
}

# --- PHASE E: Conflict / contradiction rules (V1 assumptions) ------------
CONFLICT = {
    # an opposing agent counts as "strong" above this confidence
    "strong_confidence": 70.0,
    # number of strong opposing agents that triggers a contradiction warning
    "contradiction_min_agents": 2,
    # combined opposing weighted-strength ratio that forces caution
    "severe_ratio": 0.75,
    # if opposing ratio above this -> hard veto (AVOID)
    "veto_ratio": 0.95,
    # confidence reduction applied per contradiction severity step
    "confidence_penalty": 18.0,
}

# --- PHASE F: LONG/SHORT/WAIT/AVOID entry rules (V1 assumptions) ---------
ENTRY = {
    # |consensus| must exceed this for a directional bias to exist
    "direction_min_score": 22.0,
    # consensus magnitude required to be trade-ready (LONG/SHORT)
    "entry_min_score": 45.0,
    # confidence required to be trade-ready
    "entry_min_confidence": 55.0,
    # if a directional bias exists but readiness not met -> WAIT
    # if veto/severe conflict -> AVOID
    # price extension: if price is beyond this % from nearest entry zone -> WAIT
    "max_extension_pct": 1.2,
    # minimum number of valid agents required, else AVOID (poor conditions)
    "min_valid_agents": 6,
}

ASSUMPTIONS = [
    "All agent weights are V1 starting points and are not calibrated.",
    "HTF gate raises confirmation requirements for counter-trend LTF trades; it does not block them.",
    "Confluence uses a diminishing-returns model (each correlated confirmation worth 50% of the previous).",
    "Conflict thresholds (strong=70%, >=2 opposing agents) are placeholders pending backtesting.",
    "Entry thresholds (bias>=22, entry>=45, confidence>=55) are placeholders and must be optimized.",
    "This tool is analysis/decision-support only. It does not predict the market and does not guarantee profits.",
]
