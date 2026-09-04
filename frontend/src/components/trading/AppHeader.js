import React from "react";
import { Activity, Database, Wifi, WifiOff, SlidersHorizontal, LineChart } from "lucide-react";
import { TIMEFRAMES } from "../../lib/api";
import { fmt } from "../../lib/style";

export const AppHeader = ({ ticker, live, timeframe, onTimeframe, syncStatus, onOpenSettings, onOpenBacktest }) => {
  const price = live?.last_price;
  const t = ticker || {};
  const changeRate = (t.change_rate || 0) * 100;
  const up = changeRate >= 0;
  const connected = live?.connected;

  const totalCandles = syncStatus
    ? Object.values(syncStatus.timeframes || {}).reduce((a, v) => a + (v.count || 0), 0)
    : 0;

  return (
    <header
      data-testid="app-header"
      className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center justify-between px-4 border-b border-[#1d2635] bg-[#090d14]/90 backdrop-blur-xl"
    >
      <div className="flex items-center gap-4 min-w-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-sm bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
            <Activity className="w-4 h-4 text-black" strokeWidth={2.5} />
          </div>
          <div className="leading-none">
            <div className="font-head font-extrabold text-lg tracking-wide text-white">
              MIB<span className="text-cyan-400">-</span>TRADER
            </div>
            <div className="widget-label -mt-0.5">Quant Analysis Terminal</div>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-[#1d2635]">
          <span className="font-head font-semibold text-slate-300 text-base tracking-wide">BTC/USDT</span>
          <span className="font-mono-t font-bold text-xl text-white tabular-nums" data-testid="btc-price-ticker">
            ${fmt(price, 1)}
          </span>
          <span className={`font-mono-t text-xs font-semibold ${up ? "text-emerald-400" : "text-rose-400"}`}>
            {up ? "▲" : "▼"} {fmt(Math.abs(changeRate), 2)}%
          </span>
        </div>

        <div className="hidden xl:flex items-center gap-3 pl-4 border-l border-[#1d2635] font-mono-t text-[11px] text-slate-400">
          <span>H <span className="text-slate-200">${fmt(t.high24, 0)}</span></span>
          <span>L <span className="text-slate-200">${fmt(t.low24, 0)}</span></span>
          <span>Fund <span className={t.funding_rate >= 0 ? "text-emerald-400" : "text-rose-400"}>{fmt((t.funding_rate || 0) * 100, 4)}%</span></span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-sm bg-[#0d121b] border border-[#1d2635]" data-testid="sync-status-indicator">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-mono-t text-[11px] text-slate-400">
            SQLite <span className="text-slate-200">{totalCandles.toLocaleString()}</span> candles
          </span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-[#0d121b] border border-[#1d2635]">
          {connected ? <Wifi className="w-3.5 h-3.5 text-emerald-400" /> : <WifiOff className="w-3.5 h-3.5 text-rose-400" />}
          <span className={`pulse-dot w-1.5 h-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-rose-500"}`} />
          <span className="font-mono-t text-[11px] text-slate-300">
            {connected ? (live?.ws_connected ? "MEXC · WS" : "MEXC LIVE") : "OFFLINE"}
          </span>
        </div>

        <div className="flex items-center gap-0.5 p-0.5 rounded-sm bg-[#0d121b] border border-[#1d2635]" data-testid="timeframe-selector">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              data-testid={`tf-${tf}`}
              onClick={() => onTimeframe(tf)}
              className={`font-mono-t text-[11px] font-semibold px-2 py-1 rounded-sm transition-colors ${
                timeframe === tf ? "bg-cyan-500 text-black" : "text-slate-400 hover:text-white hover:bg-[#1a2231]"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        <button
          data-testid="open-backtest"
          onClick={onOpenBacktest}
          title="Backtest"
          className="flex items-center gap-1.5 font-mono-t text-[11px] text-slate-300 px-2.5 py-1.5 rounded-sm bg-[#0d121b] border border-[#1d2635] hover:border-cyan-500/60 transition-colors"
        >
          <LineChart className="w-3.5 h-3.5 text-cyan-400" />
          <span className="hidden lg:inline">Backtest</span>
        </button>
        <button
          data-testid="open-settings"
          onClick={onOpenSettings}
          title="Config"
          className="flex items-center justify-center p-1.5 rounded-sm bg-[#0d121b] border border-[#1d2635] hover:border-cyan-500/60 transition-colors"
        >
          <SlidersHorizontal className="w-4 h-4 text-slate-300" />
        </button>
      </div>
    </header>
  );
};
