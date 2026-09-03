"""Tests for new iteration features: backtest, settings, live config."""
import os
import time
import pytest
import requests

def _load_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_env()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

EXPECTED_AGENTS = {
    "market_structure", "breakout", "fibonacci", "elliott_wave", "volume",
    "momentum", "support_resistance", "trend", "pattern", "fair_value_gap",
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Backtest ---
class TestBacktest:
    def test_backtest_default_15m(self, s):
        t0 = time.time()
        r = s.get(f"{BASE_URL}/api/backtest",
                  params={"timeframe": "15m", "lookback": 150, "forward": 8, "step": 3},
                  timeout=45)
        dur = time.time() - t0
        assert r.status_code == 200, r.text[:400]
        assert dur < 30, f"took {dur:.1f}s"
        d = r.json()
        for k in ("summary", "equity_curve", "points"):
            assert k in d, f"missing top-level {k}"
        summ = d["summary"]
        for k in ("win_rate_pct", "net_return_pct", "state_counts",
                  "directional_trades", "wins", "avg_return_per_trade_pct", "disclaimer"):
            assert k in summ, f"summary missing {k}"
        sc = summ["state_counts"]
        for state in ("LONG", "SHORT", "WAIT", "AVOID"):
            assert state in sc
        # honesty: values should be numeric and bounded
        assert 0 <= summ["win_rate_pct"] <= 100
        assert isinstance(summ["directional_trades"], int)
        assert isinstance(d["equity_curve"], list)
        assert isinstance(d["points"], list)

    @pytest.mark.parametrize("tf", ["1m", "1h", "4h"])
    def test_backtest_other_tfs(self, s, tf):
        r = s.get(f"{BASE_URL}/api/backtest",
                  params={"timeframe": tf, "lookback": 100, "forward": 5, "step": 5},
                  timeout=45)
        assert r.status_code == 200, f"{tf}: {r.text[:300]}"
        d = r.json()
        assert "summary" in d
        assert "win_rate_pct" in d["summary"]


# --- Settings ---
class TestSettings:
    def test_get_settings(self, s):
        r = s.get(f"{BASE_URL}/api/settings", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("agent_weights", "htf_gate", "confluence", "conflict", "entry", "defaults", "assumptions"):
            assert k in d, f"missing {k}"
        assert set(d["agent_weights"].keys()) == EXPECTED_AGENTS

    def test_put_settings_updates(self, s):
        # capture original
        orig = s.get(f"{BASE_URL}/api/settings", timeout=15).json()
        orig_mom = orig["agent_weights"]["momentum"]
        orig_min = orig["entry"].get("entry_min_score")

        payload = {"agent_weights": {"momentum": 2.5}, "entry": {"entry_min_score": 40}}
        r = s.put(f"{BASE_URL}/api/settings", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["agent_weights"]["momentum"] == 2.5
        assert d["entry"]["entry_min_score"] == 40

        # Verify GET persists
        d2 = s.get(f"{BASE_URL}/api/settings", timeout=15).json()
        assert d2["agent_weights"]["momentum"] == 2.5
        assert d2["entry"]["entry_min_score"] == 40

        # cleanup: reset momentum
        s.put(f"{BASE_URL}/api/settings", json={
            "agent_weights": {"momentum": orig_mom},
            "entry": {"entry_min_score": orig_min if orig_min is not None else 30},
        }, timeout=15)

    def test_settings_affects_analysis(self, s):
        # baseline
        r0 = s.get(f"{BASE_URL}/api/analysis", params={"timeframe": "15m"}, timeout=60)
        assert r0.status_code == 200
        b0 = r0.json()["brain"]
        w0 = r0.json().get("agent_weights") or r0.json().get("brain", {}).get("agent_weights")

        # big weight change
        s.put(f"{BASE_URL}/api/settings",
              json={"agent_weights": {"momentum": 5.0, "trend": 5.0}}, timeout=15)

        r1 = s.get(f"{BASE_URL}/api/analysis", params={"timeframe": "15m"}, timeout=60)
        assert r1.status_code == 200
        d1 = r1.json()
        b1 = d1["brain"]
        # brain result should be affected (score OR contributions differ)
        changed = (b0.get("consensus_score") != b1.get("consensus_score")) or \
                  (b0.get("contributions") != b1.get("contributions"))
        assert changed, "brain consensus/contributions did not change after large weight update"

        # reset
        s.post(f"{BASE_URL}/api/settings/reset", timeout=15)

    def test_settings_reset(self, s):
        # perturb
        s.put(f"{BASE_URL}/api/settings", json={"agent_weights": {"momentum": 9.9}}, timeout=15)
        r = s.post(f"{BASE_URL}/api/settings/reset", timeout=15)
        assert r.status_code == 200, r.text
        d = s.get(f"{BASE_URL}/api/settings", timeout=15).json()
        assert d["agent_weights"]["momentum"] == pytest.approx(1.2, abs=0.001), \
            f"momentum={d['agent_weights']['momentum']} after reset"
