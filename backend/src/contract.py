"""PHASE A — Standard Agent Output Contract.

Every one of the 10 analysis agents returns an AgentResult. The Brain consumes
these standardized outputs rather than containing special-case logic per agent.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

LONG = "LONG"
SHORT = "SHORT"
NEUTRAL = "NEUTRAL"

# Final Brain trade states
STATE_LONG = "LONG"
STATE_SHORT = "SHORT"
STATE_WAIT = "WAIT"
STATE_AVOID = "AVOID"


@dataclass
class AgentResult:
    agent: str                      # agent id
    direction: str                  # LONG | SHORT | NEUTRAL
    confidence: float               # 0-100
    strength: float                 # normalized magnitude 0-100
    evidence: List[str] = field(default_factory=list)
    key_levels: List[Dict[str, Any]] = field(default_factory=list)  # {label, price, type}
    timeframe: str = ""
    valid: bool = True

    def sign(self) -> int:
        if self.direction == LONG:
            return 1
        if self.direction == SHORT:
            return -1
        return 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["confidence"] = round(self.confidence, 1)
        d["strength"] = round(self.strength, 1)
        return d


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def neutral(agent: str, timeframe: str, reason: str, valid: bool = False) -> AgentResult:
    return AgentResult(
        agent=agent, direction=NEUTRAL, confidence=0.0, strength=0.0,
        evidence=[reason], key_levels=[], timeframe=timeframe, valid=valid,
    )
