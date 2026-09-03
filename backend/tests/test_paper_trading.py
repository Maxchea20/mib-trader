"""Tests for paper trading feature."""
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


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def live_price(s):
    for _ in range(10):
        r = s.get(f"{BASE_URL}/api/paper/trades", timeout=10)
        assert r.status_code == 200
        p = r.json().get("live_price")
        if p:
            return float(p)
        time.sleep(1)
    pytest.skip("No live price available")


class TestPaperTrading:
    def test_get_trades_shape(self, s):
        r = s.get(f"{BASE_URL}/api/paper/trades", timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "trades" in d and "live_price" in d
        assert isinstance(d["trades"], list)

    def test_open_defaults(self, s, live_price):
        body = {"side": "LONG", "notional_usd": 1000, "timeframe": "15m",
                "brain_state": "LONG", "consensus": 52, "confidence": 66}
        r = s.post(f"{BASE_URL}/api/paper/open", json=body, timeout=10)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["status"] == "OPEN"
        assert t["side"] == "LONG"
        assert t["entry_price"] > 0
        # SL/TP default: LONG => sl=entry*0.99, tp=entry*1.02
        assert abs(t["sl_price"] - t["entry_price"] * 0.99) < 0.01
        assert abs(t["tp_price"] - t["entry_price"] * 1.02) < 0.01
        assert abs(t["qty"] - (t["notional_usd"] / t["entry_price"])) < 1e-6
        # cleanup
        s.post(f"{BASE_URL}/api/paper/close/{t['id']}", json={}, timeout=10)

    def test_open_explicit_sl_tp(self, s, live_price):
        body = {"side": "SHORT", "notional_usd": 500, "sl_price": live_price * 1.05,
                "tp_price": live_price * 0.95, "entry_price": live_price}
        r = s.post(f"{BASE_URL}/api/paper/open", json=body, timeout=10)
        assert r.status_code == 200
        t = r.json()
        assert t["side"] == "SHORT"
        assert abs(t["sl_price"] - live_price * 1.05) < 0.01
        assert abs(t["tp_price"] - live_price * 0.95) < 0.01
        s.post(f"{BASE_URL}/api/paper/close/{t['id']}", json={}, timeout=10)

    def test_unrealized_pnl_signs(self, s, live_price):
        # LONG below current => should be positive unrealized
        entry_long = live_price * 0.5
        r = s.post(f"{BASE_URL}/api/paper/open", json={
            "side": "LONG", "notional_usd": 1000, "entry_price": entry_long,
            "sl_price": entry_long * 0.5, "tp_price": entry_long * 10,
        }, timeout=10)
        assert r.status_code == 200
        long_id = r.json()["id"]

        # SHORT above current => should be positive unrealized
        entry_short = live_price * 2.0
        r2 = s.post(f"{BASE_URL}/api/paper/open", json={
            "side": "SHORT", "notional_usd": 1000, "entry_price": entry_short,
            "sl_price": entry_short * 2, "tp_price": entry_short * 0.1,
        }, timeout=10)
        assert r2.status_code == 200
        short_id = r2.json()["id"]

        time.sleep(1)
        r3 = s.get(f"{BASE_URL}/api/paper/trades", params={"status": "OPEN"}, timeout=10)
        assert r3.status_code == 200
        by_id = {t["id"]: t for t in r3.json()["trades"]}
        lt = by_id.get(long_id)
        st = by_id.get(short_id)
        assert lt and "unrealized_pnl" in lt and "mark_price" in lt
        assert lt["unrealized_pnl"] > 0, f"LONG upnl should be > 0, got {lt['unrealized_pnl']}"
        assert st and st["unrealized_pnl"] > 0, f"SHORT upnl should be > 0, got {st['unrealized_pnl']}"

        # cleanup
        s.post(f"{BASE_URL}/api/paper/close/{long_id}", json={}, timeout=10)
        s.post(f"{BASE_URL}/api/paper/close/{short_id}", json={}, timeout=10)

    def test_close_manual(self, s, live_price):
        r = s.post(f"{BASE_URL}/api/paper/open", json={"side": "LONG", "notional_usd": 500}, timeout=10)
        tid = r.json()["id"]
        r2 = s.post(f"{BASE_URL}/api/paper/close/{tid}", json={}, timeout=10)
        assert r2.status_code == 200
        t = r2.json()
        assert t["status"] == "CLOSED"
        assert t["exit_reason"] == "MANUAL"
        assert t["exit_price"] is not None
        assert t["pnl"] is not None
        assert t["pnl_pct"] is not None

    def test_auto_close_tp(self, s, live_price):
        # Open both LONG and SHORT with TPs very close (0.02%) so any tick triggers
        r_long = s.post(f"{BASE_URL}/api/paper/open", json={
            "side": "LONG", "notional_usd": 500,
            "sl_price": live_price * 0.9, "tp_price": live_price * 1.0002,
        }, timeout=10)
        r_short = s.post(f"{BASE_URL}/api/paper/open", json={
            "side": "SHORT", "notional_usd": 500,
            "sl_price": live_price * 1.1, "tp_price": live_price * 0.9998,
        }, timeout=10)
        long_id = r_long.json()["id"]
        short_id = r_short.json()["id"]

        tp_hit = False
        for _ in range(30):
            time.sleep(1)
            trades = s.get(f"{BASE_URL}/api/paper/trades", timeout=10).json()["trades"]
            for t in trades:
                if t["id"] in (long_id, short_id) and t["status"] == "CLOSED" and t["exit_reason"] == "TP":
                    tp_hit = True
                    break
            if tp_hit:
                break

        # Cleanup any still-open
        for tid in (long_id, short_id):
            s.post(f"{BASE_URL}/api/paper/close/{tid}", json={}, timeout=10)

        assert tp_hit, "Neither LONG nor SHORT auto-closed on TP within 30s"

    def test_stats(self, s):
        r = s.get(f"{BASE_URL}/api/paper/stats", timeout=10)
        assert r.status_code == 200
        d = r.json()
        for k in ("total_trades", "open_trades", "closed_trades", "wins", "losses",
                  "win_rate_pct", "total_realized_pnl", "best_trade", "worst_trade"):
            assert k in d, f"missing {k}"
        assert d["total_trades"] == d["open_trades"] + d["closed_trades"]
        assert d["wins"] + d["losses"] == d["closed_trades"]

    def test_persistence(self, s):
        r1 = s.get(f"{BASE_URL}/api/paper/trades", timeout=10).json()
        time.sleep(1)
        r2 = s.get(f"{BASE_URL}/api/paper/trades", timeout=10).json()
        ids1 = sorted([t["id"] for t in r1["trades"] if t["status"] == "CLOSED"])
        ids2 = sorted([t["id"] for t in r2["trades"] if t["status"] == "CLOSED"])
        # closed trades should persist
        assert set(ids1).issubset(set(ids2))
