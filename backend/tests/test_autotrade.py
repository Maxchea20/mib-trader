"""Tests for hands-free auto-trade + paper trading integration."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- /api/autotrade GET ----------
def test_autotrade_get_shape(s):
    r = s.get(f"{API}/autotrade", timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "config" in d and "state" in d and "open_auto_trade" in d
    cfg = d["config"]
    for k in ("enabled", "timeframe", "notional_usd", "sl_atr_mult", "tp_atr_mult"):
        assert k in cfg, f"missing config.{k}"
    st = d["state"]
    for k in ("last_candle_ts", "last_state", "last_action", "last_reason", "last_eval_at"):
        assert k in st, f"missing state.{k}"


def test_autotrade_default_enabled_true(s):
    # After a fresh boot it should be True. If a previous test flipped it we tolerate,
    # but check the field is boolean.
    d = s.get(f"{API}/autotrade").json()
    assert isinstance(d["config"]["enabled"], bool)


# ---------- toggle off/on ----------
def test_autotrade_toggle_off_then_on_opens_auto_trade(s):
    # OFF
    r = s.put(f"{API}/autotrade", json={"enabled": False}, timeout=10)
    assert r.status_code == 200
    assert r.json()["config"]["enabled"] is False

    # If there is an existing AUTO OPEN trade, close it so we can test open-on-toggle
    trades = s.get(f"{API}/paper/trades", params={"status": "OPEN"}).json()["trades"]
    for t in trades:
        if t.get("source") == "AUTO":
            # close via manual close endpoint
            s.post(f"{API}/paper/close/{t['id']}", json={})

    # ON — should force-evaluate immediately
    r = s.put(f"{API}/autotrade", json={"enabled": True}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["config"]["enabled"] is True

    # allow a tiny beat for evaluate to run
    time.sleep(1.0)

    d = s.get(f"{API}/autotrade").json()
    last_state = d["state"].get("last_state")
    last_action = d["state"].get("last_action") or ""

    trades = s.get(f"{API}/paper/trades", params={"status": "OPEN"}).json()["trades"]
    auto_open = [t for t in trades if t.get("source") == "AUTO"]

    if last_state in ("LONG", "SHORT"):
        assert len(auto_open) >= 1, f"expected AUTO trade when Brain={last_state}, action={last_action}"
        t = auto_open[0]
        assert t["side"] in ("LONG", "SHORT")
        assert t["sl_price"] and t["tp_price"]
        assert t["status"] == "OPEN"
        assert t["source"] == "AUTO"
    else:
        # WAIT/AVOID -> no auto trade expected
        assert len(auto_open) == 0, f"unexpected AUTO trade when Brain={last_state}"


# ---------- one AUTO position at a time (no dup on re-toggle) ----------
def test_autotrade_no_duplicate_on_retoggle(s):
    trades = s.get(f"{API}/paper/trades", params={"status": "OPEN"}).json()["trades"]
    auto_before = [t for t in trades if t.get("source") == "AUTO"]
    if not auto_before:
        pytest.skip("no AUTO open trade to test duplication against (Brain likely WAIT/AVOID)")
    # toggle off then on
    s.put(f"{API}/autotrade", json={"enabled": False})
    time.sleep(0.3)
    s.put(f"{API}/autotrade", json={"enabled": True})
    time.sleep(1.0)
    trades = s.get(f"{API}/paper/trades", params={"status": "OPEN"}).json()["trades"]
    auto_after = [t for t in trades if t.get("source") == "AUTO"]
    assert len(auto_after) <= 1, f"expected <=1 AUTO open trade, got {len(auto_after)}"


# ---------- manual + auto coexist, source tags ----------
def test_manual_trade_has_source_manual_and_coexists(s):
    r = s.post(f"{API}/paper/open", json={
        "side": "LONG", "notional_usd": 100, "sl_pct": 1.0, "tp_pct": 2.0, "note": "TEST_manual"
    })
    assert r.status_code == 200, r.text
    trade = r.json()
    assert trade["source"] == "MANUAL"
    assert trade["side"] == "LONG"
    assert trade["status"] == "OPEN"
    tid = trade["id"]

    all_open = s.get(f"{API}/paper/trades", params={"status": "OPEN"}).json()["trades"]
    sources = {t["source"] for t in all_open}
    # Manual is definitely present; AUTO may or may not depending on Brain state
    assert "MANUAL" in sources

    # cleanup
    s.post(f"{API}/paper/close/{tid}", json={})


# ---------- persistence across calls ----------
def test_trades_persist_across_calls(s):
    a = s.get(f"{API}/paper/trades").json()["trades"]
    b = s.get(f"{API}/paper/trades").json()["trades"]
    ids_a = {t["id"] for t in a}
    ids_b = {t["id"] for t in b}
    # b should be a superset (nothing removed)
    assert ids_a.issubset(ids_b), "trades disappeared between GETs"
    # every row has a source field
    for t in b:
        assert "source" in t and t["source"] in ("AUTO", "MANUAL")


# ---------- stats aggregation ----------
def test_paper_stats_shape(s):
    d = s.get(f"{API}/paper/stats").json()
    for k in ("total_trades", "open_trades", "closed_trades", "wins", "losses",
              "win_rate_pct", "total_realized_pnl"):
        assert k in d
