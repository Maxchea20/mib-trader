import React from "react";
import { Layers } from "lucide-react";
import { dirStyle, fmt } from "../../lib/style";

export const MultiTimeframeRegime = ({ htf }) => {
  if (!htf) return null;
  const st = dirStyle(htf.regime);
  const per = htf.per_timeframe || {};
  return (
    <div className="panel p-3" data-testid="htf-regime-panel">
      <div className="flex items-center gap-2 mb-2">
        <Layers className="w-3.5 h-3.5 text-purple-400" />
        <span className="widget-label">HTF Market Regime · 4h / 1d Context</span>
      </div>
      <div className="flex items-center justify-between">
        <div>
          <div className={`font-head font-bold text-2xl ${st.text}`}>{htf.regime}</div>
          <div className="widget-label">Regime Context Gate</div>
        </div>
        <div className="text-right">
          <div className="font-mono-t font-bold text-xl" style={{ color: htf.regime_score >= 0 ? "#00f59b" : htf.regime_score < 0 ? "#ff3b56" : "#94a3b8" }}>
            {htf.regime_score >= 0 ? "+" : ""}{fmt(htf.regime_score, 0)}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3 pt-2 border-t border-[#1d2635]">
        {Object.entries(per).map(([tf, score]) => (
          <div key={tf} className="flex items-center justify-between">
            <span className="font-mono-t text-[11px] text-slate-400 uppercase">{tf}</span>
            <span className="font-mono-t text-[11px] font-bold" style={{ color: score >= 0 ? "#00f59b" : "#ff3b56" }}>
              {score >= 0 ? "+" : ""}{fmt(score, 0)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
