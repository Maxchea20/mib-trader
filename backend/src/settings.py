"""Runtime-mutable configuration.

config.py holds the V1 DEFAULTS. This module keeps a live, editable copy so the
Settings panel can tune agent weights and HTF/conflict/entry thresholds and see
the Brain decision update instantly. All modules read the current values here.
"""
import copy
from . import config

_STATE = {
    "agent_weights": copy.deepcopy(config.AGENT_WEIGHTS),
    "htf_gate": copy.deepcopy(config.HTF_GATE),
    "confluence": copy.deepcopy(config.CONFLUENCE),
    "conflict": copy.deepcopy(config.CONFLICT),
    "entry": copy.deepcopy(config.ENTRY),
}


def weights():
    return _STATE["agent_weights"]


def htf_gate():
    return _STATE["htf_gate"]


def confluence():
    return _STATE["confluence"]


def conflict():
    return _STATE["conflict"]


def entry():
    return _STATE["entry"]


def snapshot():
    return {
        "config_version": config.CONFIG_VERSION,
        "agent_weights": copy.deepcopy(_STATE["agent_weights"]),
        "htf_gate": copy.deepcopy(_STATE["htf_gate"]),
        "confluence": copy.deepcopy(_STATE["confluence"]),
        "conflict": copy.deepcopy(_STATE["conflict"]),
        "entry": copy.deepcopy(_STATE["entry"]),
        "defaults": {
            "agent_weights": config.AGENT_WEIGHTS,
            "htf_gate": config.HTF_GATE,
            "confluence": config.CONFLUENCE,
            "conflict": config.CONFLICT,
            "entry": config.ENTRY,
        },
        "assumptions": config.ASSUMPTIONS,
    }


def update(payload: dict) -> dict:
    """Merge numeric overrides. Only existing keys are accepted."""
    for section in ("agent_weights", "htf_gate", "confluence", "conflict", "entry"):
        if section not in payload or not isinstance(payload[section], dict):
            continue
        target = _STATE[section]
        for k, v in payload[section].items():
            if k not in target:
                continue
            # keep list-valued config keys (e.g. level_agents) untouched
            if isinstance(target[k], list):
                continue
            try:
                target[k] = float(v)
            except (TypeError, ValueError):
                continue
    return snapshot()


def reset() -> dict:
    _STATE["agent_weights"] = copy.deepcopy(config.AGENT_WEIGHTS)
    _STATE["htf_gate"] = copy.deepcopy(config.HTF_GATE)
    _STATE["confluence"] = copy.deepcopy(config.CONFLUENCE)
    _STATE["conflict"] = copy.deepcopy(config.CONFLICT)
    _STATE["entry"] = copy.deepcopy(config.ENTRY)
    return snapshot()
