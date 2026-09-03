import React, { useEffect, useState, useCallback } from "react";
import { TrendingUp, TrendingDown, Wallet, Bot, Plus } from "lucide-react";
import {
  openPaperTrade, closePaperTrade, getPaperTrades, getPaperStats,
  getAutotrade, updateAutotrade,
} from "../../lib/api";
import { dirStyle, fmt } from "../../lib/style";

const fmtTime = (ts) => (ts ? new Date(ts * 1000).toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—");

const Pnl = ({ v, pct }) => {
  if (v === null || v === undefined) return <span className="text-slate-500">—</span>;
  const c = v >= 0 ? "text-emerald-400" : "text-rose-400";
  return <span className={`font-mono-t ${c}`}>{v >= 0 ? "+" : ""}${fmt(v, 2)} <span className="text-[10px] opacity-70">({v >= 0 ? "+" : ""}{fmt(pct, 2)}%)</span></span>;
};

const TradeTable = ({ rows, onClose, testid }) => (
  <div className="overflow-x-auto" data-testid={testid}>
    <table className="w-full text-left">
      <thead>
        <tr className="widget-label border-b border-[#1d2635]">
          <th className="px-3 py-2">Src</th>
          <th className="px-3 py-2">Side</th>
          <th className="px-3 py-2">Status</th>
          <th className="px-3 py-2">Entry</th>
          <th className="px-3 py-2">SL</th>
          <th className="px-3 py-2">TP</th>
          <th className="px-3 py-2">Exit</th>
          <th className="px-3 py-2">PnL</th>
          <th className="px-3 py-2">Opened</th>
          <th className="px-3 py-2"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((t) => {
          const st = dirStyle(t.side);
          const isOpen = t.status === "OPEN";
          return (
            <tr key={t.id} className="border-b border-[#161f2e] font-mono-t text-[11px]" data-testid={`paper-row-${t.id}`}>
              <td className="px-3 py-2">
                <span className={`text-[9px] px-1 py-0.5 rounded-sm border ${t.source === "AUTO" ? "border-cyan-500/50 text-cyan-400" : "border-slate-600 text-slate-400"}`}>
                  {t.source || "MANUAL"}
                </span>
              </td>
              <td className={`px-3 py-2 font-bold ${st.text}`}>{t.side}</td>
              <td className="px-3 py-2">
                <span className={isOpen ? "text-cyan-400" : "text-slate-400"}>{t.status}</span>
                {!isOpen && t.exit_reason && <span className="text-slate-600 ml-1">·{t.exit_reason}</span>}
              </td>
              <td className="px-3 py-2 text-slate-200">${fmt(t.entry_price, 1)}</td>
              <td className="px-3 py-2 text-rose-400/80">${fmt(t.sl_price, 1)}</td>
              <td className="px-3 py-2 text-emerald-400/80">${fmt(t.tp_price, 1)}</td>
              <td className="px-3 py-2 text-slate-300">{t.exit_price ? `$${fmt(t.exit_price, 1)}` : (isOpen ? `~$${fmt(t.mark_price, 1)}` : "—")}</td>
              <td className="px-3 py-2">{isOpen ? <Pnl v={t.unrealized_pnl} pct={t.unrealized_pnl_pct} /> : <Pnl v={t.pnl} pct={t.pnl_pct} />}</td>
              <td className="px-3 py-2 text-slate-500">{fmtTime(t.opened_at)}</td>
              <td className="px-3 py-2">
                {isOpen && (
                  <button onClick={() => onClose(t.id)} data-testid={`paper-close-${t.id}`}
                    className="text-[10px] px-2 py-0.5 rounded-sm border border-slate-600 text-slate-300 hover:border-rose-500 hover:text-rose-400">
                    Close
                  </button>
                )}
              </td>
            </tr>
          );
        })}
        {rows.length === 0 && (
          <tr><td colSpan="10" className="px-3 py-6 text-center font-mono-t text-[11px] text-slate-600">No trades yet</td></tr>
        )}
      </tbody>
    </table>
  </div>
);

export const PaperTradingPanel = ({ brain, livePrice, timeframe }) => {
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [markPrice, setMarkPrice] = useState(null);
  const [auto, setAuto] = useState(null);
  const [tab, setTab] = useState("open");
  const [showForm, setShowForm] = useState(false);

  const bias = brain?.direction && brain.direction !== "NEUTRAL" ? brain.direction : "LONG";
  const [side, setSide] = useState(bias);
  const [notional, setNotional] = useState(1000);
  const [slPct, setSlPct] = useState(1.0);
  const [tpPct, setTpPct] = useState(2.0);
  const [busy, setBusy] = useState(false);

  const entry = livePrice || markPrice;
  const slPrice = entry ? (side === "LONG" ? entry * (1 - slPct / 100) : entry * (1 + slPct / 100)) : null;
  const tpPrice = entry ? (side === "LONG" ? entry * (1 + tpPct / 100) : entry * (1 - tpPct / 100)) : null;

  const refresh = useCallback(async () => {
    try {
      const [d, s, a] = await Promise.all([getPaperTrades(), getPaperStats(), getAutotrade()]);
      setTrades(d.trades || []);
      setMarkPrice(d.live_price);
      setStats(s);
      setAuto(a);
    } catch (e) {}
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 3000);
    return () => clearInterval(iv);
  }, [refresh]);

  const toggleAuto = async () => {
    const next = !(auto?.config?.enabled);
    setAuto((p) => ({ ...(p || {}), config: { ...(p?.config || {}), enabled: next } }));
    try { const a = await updateAutotrade({ enabled: next }); setAuto(a); refresh(); } catch (e) {}
  };

  const submit = async () => {
    setBusy(true);
    try {
      await openPaperTrade({
        side, notional_usd: Number(notional),
        entry_price: entry || undefined,
        sl_price: entry ? slPrice : undefined,
        tp_price: entry ? tpPrice : undefined,
        timeframe, brain_state: brain?.state || "", consensus: brain?.consensus_score || 0,
        confidence: brain?.confidence || 0,
      });
      await refresh();
      setShowForm(false);
      setTab("open");
    } catch (e) {}
    setBusy(false);
  };

  const doClose = async (id) => { await closePaperTrade(id); refresh(); };

  const openTrades = trades.filter((t) => t.status === "OPEN");
  const autoOn = auto?.config?.enabled;

  return (
    <div className="mt-4" data-testid="paper-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2 px-0.5">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-emerald-400" />
          <span className="font-head font-bold text-slate-200 tracking-wide text-lg">PAPER TRADING</span>
          <span className="widget-label">Persistent · Simulated · Auto SL/TP</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Auto-trade toggle */}
          <button
            onClick={toggleAuto}
            data-testid="autotrade-toggle"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-sm border font-mono-t text-[11px] transition-colors ${
              autoOn ? "border-cyan-500/60 bg-cyan-500/10 text-cyan-300" : "border-[#1d2635] bg-[#0d121b] text-slate-400"
            }`}
          >
            <Bot className={`w-3.5 h-3.5 ${autoOn ? "text-cyan-400" : "text-slate-500"}`} />
            <span>AUTO-TRADE</span>
            <span className={`w-8 h-4 rounded-full relative transition-colors ${autoOn ? "bg-cyan-500" : "bg-slate-700"}`}>
              <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-black transition-all ${autoOn ? "left-4" : "left-0.5"}`} />
            </span>
            <span className={autoOn ? "text-emerald-400" : "text-slate-500"}>{autoOn ? "ON" : "OFF"}</span>
          </button>

          <button
            onClick={() => setShowForm((v) => !v)}
            data-testid="paper-new-toggle"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-[#1d2635] bg-[#0d121b] text-slate-300 hover:border-cyan-500/60 font-mono-t text-[11px]"
          >
            <Plus className="w-3.5 h-3.5" /> New Trade
          </button>
        </div>
      </div>

      {/* auto-trade status line */}
      {auto && (
        <div className="font-mono-t text-[10px] text-slate-500 mb-2 px-0.5" data-testid="autotrade-status">
          Engine: <span className={autoOn ? "text-cyan-400" : "text-slate-500"}>{autoOn ? "running" : "paused"}</span>
          {" · "}TF <span className="text-slate-300">{auto.config?.timeframe}</span>
          {" · "}size <span className="text-slate-300">${fmt(auto.config?.notional_usd, 0)}</span>
          {" · "}last: <span className="text-slate-300">{auto.state?.last_action || "—"}</span>
          {auto.state?.last_reason ? ` (${auto.state.last_reason})` : ""}
        </div>
      )}

      {/* stats */}
      {stats && (
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3" data-testid="paper-stats">
          <div className="panel p-2"><div className="widget-label">Trades</div><div className="font-mono-t text-lg text-slate-100">{stats.total_trades}</div></div>
          <div className="panel p-2"><div className="widget-label">Open</div><div className="font-mono-t text-lg text-cyan-400">{stats.open_trades}</div></div>
          <div className="panel p-2"><div className="widget-label">Win rate</div><div className="font-mono-t text-lg" style={{ color: stats.win_rate_pct >= 50 ? "#00f59b" : "#ffb800" }}>{fmt(stats.win_rate_pct, 1)}%</div></div>
          <div className="panel p-2"><div className="widget-label">Realized PnL</div><div className="font-mono-t text-lg" style={{ color: stats.total_realized_pnl >= 0 ? "#00f59b" : "#ff3b56" }} data-testid="paper-total-pnl">{stats.total_realized_pnl >= 0 ? "+" : ""}${fmt(stats.total_realized_pnl, 2)}</div></div>
          <div className="panel p-2"><div className="widget-label">Best</div><div className="font-mono-t text-lg text-emerald-400">+${fmt(stats.best_trade, 2)}</div></div>
          <div className="panel p-2"><div className="widget-label">Worst</div><div className="font-mono-t text-lg text-rose-400">${fmt(stats.worst_trade, 2)}</div></div>
        </div>
      )}

      {/* manual new-trade form */}
      {showForm && (
        <div className="panel p-4 mb-3" data-testid="paper-new-form">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex gap-2">
              <button onClick={() => setSide("LONG")} data-testid="paper-side-long"
                className={`flex items-center gap-1.5 px-4 py-2 rounded-sm font-head font-bold ${side === "LONG" ? "bg-emerald-950/60 border border-emerald-500/60 text-emerald-400" : "bg-[#0d121b] border border-[#1d2635] text-slate-400"}`}>
                <TrendingUp className="w-4 h-4" /> LONG
              </button>
              <button onClick={() => setSide("SHORT")} data-testid="paper-side-short"
                className={`flex items-center gap-1.5 px-4 py-2 rounded-sm font-head font-bold ${side === "SHORT" ? "bg-rose-950/60 border border-rose-500/60 text-rose-400" : "bg-[#0d121b] border border-[#1d2635] text-slate-400"}`}>
                <TrendingDown className="w-4 h-4" /> SHORT
              </button>
            </div>
            <label className="flex flex-col gap-1">
              <span className="widget-label">Entry (live)</span>
              <div className="font-mono-t text-sm text-white bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1.5 w-28">${fmt(entry, 1)}</div>
            </label>
            <label className="flex flex-col gap-1">
              <span className="widget-label">Size $</span>
              <input type="number" value={notional} onChange={(e) => setNotional(e.target.value)} data-testid="paper-notional"
                className="font-mono-t text-sm text-white bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1.5 w-24" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="widget-label">SL %</span>
              <input type="number" step="0.1" value={slPct} onChange={(e) => setSlPct(+e.target.value)} data-testid="paper-sl-pct"
                className="font-mono-t text-sm text-white bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1.5 w-20" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="widget-label">TP %</span>
              <input type="number" step="0.1" value={tpPct} onChange={(e) => setTpPct(+e.target.value)} data-testid="paper-tp-pct"
                className="font-mono-t text-sm text-white bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1.5 w-20" />
            </label>
            <div className="font-mono-t text-[11px] flex flex-col gap-0.5">
              <span className="text-rose-400">SL ${fmt(slPrice, 1)}</span>
              <span className="text-emerald-400">TP ${fmt(tpPrice, 1)}</span>
            </div>
            <button onClick={submit} disabled={busy} data-testid="paper-submit"
              className="px-5 py-2 rounded-sm font-head font-bold text-black bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50">
              {busy ? "Opening…" : `OPEN ${side}`}
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-1 mb-2">
        {[["open", `Open Positions (${openTrades.length})`], ["history", `History (${trades.length})`]].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} data-testid={`paper-tab-${k}`}
            className={`font-mono-t text-[11px] px-3 py-1.5 rounded-sm transition-colors ${tab === k ? "bg-cyan-500 text-black" : "bg-[#0d121b] text-slate-400 border border-[#1d2635] hover:text-white"}`}>
            {label}
          </button>
        ))}
      </div>

      <div className="panel">
        <TradeTable rows={tab === "open" ? openTrades : trades} onClose={doClose} testid={`paper-table-${tab}`} />
      </div>
    </div>
  );
};
