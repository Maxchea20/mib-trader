"""MIB-Trader backend API tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://mib-trader-live.preview.emergentagent.com").rstrip("/")
TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
EXPECTED_AGENTS = {
    "market_structure", "breakout", "fibonacci", "elliott_wave", "volume",
    "momentum", "support_resistance", "trend", "pattern", "fair_value_gap",
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Root / config ---
class TestRootAndConfig:
    def test_root(self, s):
        r = s.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("app") == "MIB-Trader"
        assert d.get("timeframes") == TIMEFRAMES

    def test_config(self, s):
        r = s.get(f"{BASE_URL}/api/config", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("config_version", "agent_weights", "htf_gate", "confluence", "conflict", "entry", "assumptions"):
            assert k in d, f"missing {k}"
        assert set(d["agent_weights"].keys()) == EXPECTED_AGENTS
        assert isinstance(d["assumptions"], list) and len(d["assumptions"]) > 0


# --- Market data ---
class TestMarket:
    def test_ticker(self, s):
        r = s.get(f"{BASE_URL}/api/market/ticker", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("connected") is True
        assert d.get("source") in ("mexc", "mexc_ws", "mexc_rest")
        assert isinstance(d.get("last_price"), (int, float))
        assert isinstance(d.get("ticker"), dict)

    @pytest.mark.parametrize("tf", TIMEFRAMES)
    def test_candles_all_tfs(self, s, tf):
        r = s.get(f"{BASE_URL}/api/market/candles", params={"timeframe": tf, "limit": 200}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        candles = d.get("candles") if isinstance(d, dict) else d
        assert isinstance(candles, list) and len(candles) > 0
        # ascending ts
        ts = [c["ts"] for c in candles]
        assert ts == sorted(ts)
        # OHLCV fields
        c0 = candles[0]
        for f in ("ts", "open", "high", "low", "close", "volume"):
            assert f in c0

    def test_sync_status(self, s):
        r = s.get(f"{BASE_URL}/api/market/sync-status", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # Expect per-timeframe entries
        per_tf = d.get("timeframes") or d.get("per_timeframe") or d
        # allow flexible shape - just verify each tf appears somewhere
        text = str(d)
        for tf in TIMEFRAMES:
            assert tf in text

    def test_sync_trigger(self, s):
        r = s.post(f"{BASE_URL}/api/market/sync", params={"timeframe": "5m"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") in ("ok", "success", "OK")

    def test_gaps(self, s):
        r = s.get(f"{BASE_URL}/api/market/gaps", params={"timeframe": "1h"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        gaps = d.get("gaps") if isinstance(d, dict) else d
        assert isinstance(gaps, list)


# --- Analysis / Brain ---
class TestAnalysis:
    @pytest.mark.parametrize("tf", TIMEFRAMES)
    def test_analysis_all_tfs(self, s, tf):
        r = s.get(f"{BASE_URL}/api/analysis", params={"timeframe": tf}, timeout=60)
        assert r.status_code == 200, f"{tf}: {r.text[:400]}"
        d = r.json()
        agents = d.get("agents")
        assert isinstance(agents, list) and len(agents) == 10, f"{tf}: got {len(agents) if agents else 0}"
        ids = {a["agent"] for a in agents}
        assert ids == EXPECTED_AGENTS, f"{tf}: mismatch {ids ^ EXPECTED_AGENTS}"
        for a in agents:
            for f in ("agent", "direction", "confidence", "strength", "evidence", "key_levels", "timeframe", "valid"):
                assert f in a, f"{tf}/{a.get('agent')}: missing {f}"
            assert a["direction"] in ("LONG", "SHORT", "NEUTRAL")
            assert 0 <= a["confidence"] <= 100

        htf = d.get("htf_regime")
        assert isinstance(htf, dict)
        assert "regime" in htf and "regime_score" in htf and "per_timeframe" in htf

        b = d.get("brain")
        assert isinstance(b, dict)
        assert b["state"] in ("LONG", "SHORT", "WAIT", "AVOID")
        for f in ("direction", "consensus_score", "confidence", "confluence_zones", "conflict", "htf_gate", "reasons", "why_state", "contributions"):
            assert f in b, f"{tf}: brain missing {f}"
        assert -100 <= b["consensus_score"] <= 100
        # sign vs direction consistency
        if b["direction"] == "LONG":
            assert b["consensus_score"] >= 0 or b["state"] in ("WAIT", "AVOID")
        elif b["direction"] == "SHORT":
            assert b["consensus_score"] <= 0 or b["state"] in ("WAIT", "AVOID")

    def test_agent_single(self, s):
        r = s.get(f"{BASE_URL}/api/agents/momentum", params={"timeframe": "15m"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("agent") == "momentum"
        assert d.get("direction") in ("LONG", "SHORT", "NEUTRAL")

    def test_agent_bad_id(self, s):
        r = s.get(f"{BASE_URL}/api/agents/bad_id", params={"timeframe": "15m"}, timeout=15)
        # accept 200 with error payload OR 4xx
        if r.status_code == 200:
            d = r.json()
            assert "unknown_agent" in str(d).lower() or d.get("error") == "unknown_agent"
        else:
            assert r.status_code in (400, 404, 422)
