"""AGENT 6 — MOMENTUM.
Composite of RSI, MACD, ROC and EMA slope normalized to [-100, +100].
-100 = strongly bearish, 0 = neutral, +100 = strongly bullish.
"""
import numpy as np
from ..contract import AgentResult, LONG, SHORT, NEUTRAL, clamp, neutral
from ..indicators import arrays, rsi, macd, roc, ema

AGENT_ID = "momentum"


def analyze(candles, timeframe: str) -> AgentResult:
    if len(candles) < 40:
        return neutral(AGENT_ID, timeframe, "Not enough candles")
    a = arrays(candles)
    closes = a["close"]

    _rsi = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    _roc = roc(closes, 12)
    e = ema(closes, 20)
    slope = (e[-1] - e[-5]) / max(abs(e[-5]), 1e-9) * 100 if len(e) >= 5 else 0.0

    # Normalize each component to [-100, 100]
    rsi_n = clamp((_rsi - 50) * 2, -100, 100)
    macd_n = clamp(hist / max(abs(closes[-1]) * 0.002, 1e-9) * 100, -100, 100)
    roc_n = clamp(_roc * 12, -100, 100)
    slope_n = clamp(slope * 25, -100, 100)

    composite = 0.30 * rsi_n + 0.30 * macd_n + 0.20 * roc_n + 0.20 * slope_n
    composite = clamp(composite, -100, 100)

    evidence = [
        f"RSI(14)={_rsi:.1f}",
        f"MACD hist={hist:.2f} ({'bullish' if hist > 0 else 'bearish'})",
        f"ROC(12)={_roc:.2f}%",
        f"EMA20 slope={slope:+.2f}%",
        f"Composite momentum={composite:+.0f}",
    ]
    if composite > 12:
        direction = LONG
    elif composite < -12:
        direction = SHORT
    else:
        direction = NEUTRAL
    confidence = clamp(35 + abs(composite) * 0.55, 0, 94)
    strength = abs(composite)
    return AgentResult(AGENT_ID, direction, confidence, strength, evidence,
                       [], timeframe, valid=True)
