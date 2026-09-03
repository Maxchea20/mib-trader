import React, { useState } from "react";
import { X, Play, AlertTriangle } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { runBacktest } from "../../lib/api";
import { dirStyle, fmt } from "../../lib/style";

const Stat = ({ label, value, color, testid }) => (
  <div className="panel p-2.5">
    <div className="widget-label">{label}</div>
    <div className="font-mono-t font-bold text-lg mt-0.5" style={{ color: color || "#e2e8f0" }} data-testid={testid}>{value}</div>
  </div>
);

export const BacktestModal = ({ open, onClose, timeframe }) => {
  const [forward, setForward] = useState(8);
  const [lookback, setLookback] = useState(150);
  const [step, setStep] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!open) return null;

  const run = async () => {
    setLoading(true); setError(null);
    try {
      const d = await runBacktest({ timeframe, lookback, forward, step });
      if (d.error) setError(d.error);
      else setResult(d);
    } catch (e) { setError("request failed"); }
    setLoading(false);
  };

  const s = result?.summary;
  const netColor = s ? (s.net_return_pct >= 0 ? "#00f59b" : "#ff3b56") : "#e2e8f0";
  const curve = (result?.equity_curve || []).map((p, i) => ({ i, equity: p.equity }));

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="panel max-w-3xl w-full p-5 fade-up max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="backtest-modal">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="font-head font-bold text-2xl text-white tracking-wide">BACKTEST · BRAIN REPLAY</div>
            <div className="font-mono-t text-[10px] text-slate-500">Replays stored SQLite history through the Brain on {timeframe}</div>
          </div>
          <button onClick={onClose} data-testid="backtest-close" className="text-slate-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex flex-wrap items-end gap-3 mb-4">
          <label className="flex flex-col gap-1">
            <span className="widget-label">Forward candles</span>
            <input type="number" min="1" max="48" value={forward} onChange={(e) => setForward(+e.target.value)}
              data-testid="backtest-forward" className="w-24 bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1 font-mono-t text-sm text-white" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="widget-label">History window</span>
            <input type="number" min="20" max="400" value={lookback} onChange={(e) => setLookback(+e.target.value)}
              data-testid="backtest-lookback" className="w-24 bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1 font-mono-t text-sm text-white" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="widget-label">Step</span>
            <input type="number" min="1" max="10" value={step} onChange={(e) => setStep(+e.target.value)}
              data-testid="backtest-step" className="w-20 bg-[#0d121b] border border-[#1d2635] rounded-sm px-2 py-1 font-mono-t text-sm text-white" />
          </label>
          <button onClick={run} disabled={loading} data-testid="backtest-run"
            className="flex items-center gap-1.5 font-mono-t text-sm font-semibold px-4 py-1.5 rounded-sm bg-cyan-500 text-black hover:bg-cyan-400 disabled:opacity-50">
            <Play className="w-3.5 h-3.5" /> {loading ? "Running…" : "Run Backtest"}
          </button>
        </div>

        {error && <div className="font-mono-t text-xs text-rose-400 mb-3">Error: {error}</div>}

        {s && (
          <div data-testid="backtest-results">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
              <Stat label="Win rate" value={`${fmt(s.win_rate_pct, 1)}%`} color={s.win_rate_pct >= 50 ? "#00f59b" : "#ffb800"} testid="backtest-winrate" />
              <Stat label="Net return (gross)" value={`${s.net_return_pct >= 0 ? "+" : ""}${fmt(s.net_return_pct, 2)}%`} color={netColor} testid="backtest-net" />
              <Stat label="Directional trades" value={s.directional_trades} />
              <Stat label="Avg / trade" value={`${fmt(s.avg_return_per_trade_pct, 3)}%`} color={s.avg_return_per_trade_pct >= 0 ? "#00f59b" : "#ff3b56"} />
            </div>

            <div className="grid grid-cols-4 gap-2 mb-4">
              {["LONG", "SHORT", "WAIT", "AVOID"].map((st) => (
                <div key={st} className="panel p-2 text-center">
                  <div className={`font-head font-bold text-sm ${dirStyle(st).text}`}>{st}</div>
                  <div className="font-mono-t text-lg text-slate-200">{s.state_counts[st] || 0}</div>
                </div>
              ))}
            </div>

            <div className="panel p-3 mb-3">
              <div className="widget-label mb-2">Cumulative signed return (directional signals)</div>
              <div className="h-40" data-testid="backtest-equity-curve">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={curve}>
                    <defs>
                      <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="i" hide />
                    <YAxis width={38} tick={{ fill: "#5b6b82", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                    <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
                    <Tooltip contentStyle={{ background: "#0d121b", border: "1px solid #1d2635", fontFamily: "JetBrains Mono", fontSize: 11 }} />
                    <Area type="monotone" dataKey="equity" stroke="#38bdf8" fill="url(#eq)" strokeWidth={1.5} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="flex items-start gap-2 font-mono-t text-[10px] text-amber-500/90 bg-amber-500/5 border border-amber-500/20 rounded-sm p-2">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{s.disclaimer}</span>
            </div>
          </div>
        )}

        {!s && !loading && !error && (
          <div className="font-mono-t text-[11px] text-slate-500 py-8 text-center">
            Configure parameters and run to replay the Brain over stored history.
          </div>
        )}
      </div>
    </div>
  );
};
