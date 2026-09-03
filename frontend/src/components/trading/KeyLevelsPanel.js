import React from "react";
import { Crosshair, Gauge } from "lucide-react";
import { dirStyle, fmt } from "../../lib/style";

const findAgent = (agents, id) => agents?.find((a) => a.agent === id);

const StatusChip = ({ label, agent, testid }) => {
  const st = dirStyle(agent?.direction);
  return (
    <div className="panel p-2" data-testid={testid}>
      <div className="widget-label">{label}</div>
      <div className="flex items-center justify-between mt-1">
        <span className={`font-head font-bold text-sm ${st.text}`}>{agent?.direction || "—"}</span>
        <span className="font-mono-t text-[11px] text-slate-400">{fmt(agent?.confidence, 0)}%</span>
      </div>
    </div>
  );
};

export const KeyLevelsPanel = ({ analysis, onHover }) => {
  const agents = analysis?.agents || [];
  const sr = findAgent(agents, "support_resistance");
  const fib = findAgent(agents, "fibonacci");
  const fvg = findAgent(agents, "fair_value_gap");
  const price = analysis?.price;

  const supports = (sr?.key_levels || []).filter((l) => l.type === "support");
  const resistances = (sr?.key_levels || []).filter((l) => l.type === "resistance");
  const fibLevels = (fib?.key_levels || []).slice(0, 6);
  const fvgZones = (fvg?.key_levels || []);

  return (
    <div className="panel p-3" data-testid="key-levels-panel">
      <div className="flex items-center gap-2 mb-2">
        <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
        <span className="widget-label">Key Trading Levels · Confluence Inspector</span>
      </div>

      {/* Status strip */}
      <div className="grid grid-cols-5 gap-1.5 mb-3">
        <StatusChip label="Breakout" agent={findAgent(agents, "breakout")} testid="status-breakout" />
        <StatusChip label="Momentum" agent={findAgent(agents, "momentum")} testid="status-momentum" />
        <StatusChip label="Volume" agent={findAgent(agents, "volume")} testid="status-volume" />
        <StatusChip label="Trend" agent={findAgent(agents, "trend")} testid="status-trend" />
        <StatusChip label="Pattern" agent={findAgent(agents, "pattern")} testid="status-pattern" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* S/R */}
        <div onMouseEnter={() => onHover?.("support")} onMouseLeave={() => onHover?.(null)}>
          <div className="widget-label mb-1.5">Support / Resistance</div>
          <div className="space-y-1">
            {resistances.map((l, i) => (
              <div key={`r${i}`} className="flex justify-between font-mono-t text-[11px]">
                <span className="text-rose-400/90">{l.label}</span>
                <span className="text-slate-200">${fmt(l.price, 1)}</span>
              </div>
            ))}
            {price && <div className="flex justify-between font-mono-t text-[11px] border-y border-[#1d2635] py-0.5 my-0.5">
              <span className="text-cyan-400">PRICE</span><span className="text-cyan-400 font-bold">${fmt(price, 1)}</span>
            </div>}
            {supports.map((l, i) => (
              <div key={`s${i}`} className="flex justify-between font-mono-t text-[11px]">
                <span className="text-emerald-400/90">{l.label}</span>
                <span className="text-slate-200">${fmt(l.price, 1)}</span>
              </div>
            ))}
            {supports.length === 0 && resistances.length === 0 && <div className="font-mono-t text-[10px] text-slate-600">no zones</div>}
          </div>
        </div>

        {/* Fibonacci */}
        <div data-testid="fibonacci-levels-list" onMouseEnter={() => onHover?.("fibonacci")} onMouseLeave={() => onHover?.(null)}>
          <div className="widget-label mb-1.5">Fibonacci</div>
          <div className="space-y-1">
            {fibLevels.map((l, i) => (
              <div key={i} className="flex justify-between font-mono-t text-[11px]">
                <span className="text-purple-400/90">{l.label}</span>
                <span className="text-slate-200">${fmt(l.price, 1)}</span>
              </div>
            ))}
            {fibLevels.length === 0 && <div className="font-mono-t text-[10px] text-slate-600">—</div>}
          </div>
        </div>

        {/* FVG */}
        <div data-testid="fvg-zones-list" onMouseEnter={() => onHover?.("fvg")} onMouseLeave={() => onHover?.(null)}>
          <div className="widget-label mb-1.5">Fair Value Gaps</div>
          <div className="space-y-1">
            {fvgZones.map((l, i) => (
              <div key={i} className="flex justify-between font-mono-t text-[11px]">
                <span className={l.type === "fvg_bullish" ? "text-emerald-400/90" : "text-rose-400/90"}>
                  {l.type === "fvg_bullish" ? "Bull" : "Bear"} {l.mitigated ? "◔" : "●"}
                </span>
                <span className="text-slate-200">${fmt(l.low, 0)}–{fmt(l.high, 0)}</span>
              </div>
            ))}
            {fvgZones.length === 0 && <div className="font-mono-t text-[10px] text-slate-600">no gaps</div>}
          </div>
        </div>
      </div>
    </div>
  );
};
