import React from "react";
import { ListTree } from "lucide-react";
import { dirStyle } from "../../lib/style";

export const ExplainabilityPanel = ({ brain }) => {
  if (!brain || brain.error) return null;
  const st = dirStyle(brain.state);
  return (
    <div className="panel p-4 fade-up" data-testid="explainability-panel">
      <div className="flex items-center gap-2 mb-3">
        <ListTree className="w-3.5 h-3.5 text-cyan-400" />
        <span className="widget-label">Why {brain.state}? — Traceable Reasoning</span>
      </div>

      <div className="space-y-1.5 mb-3" data-testid="brain-reasons-list">
        {(brain.reasons || []).map((r, i) => (
          <div key={i} className="flex gap-2 items-start">
            <span className="mt-1 w-1 h-1 rounded-full flex-shrink-0" style={{ background: st.raw === "none" ? "#94a3b8" : st.raw }} />
            <span className="font-mono-t text-[11px] text-slate-300 leading-relaxed">{r}</span>
          </div>
        ))}
      </div>

      <div className={`mt-3 pt-3 border-t border-[#1d2635]`}>
        <div className="widget-label mb-1.5">State Decision Logic</div>
        <div className="space-y-1">
          {(brain.why_state || []).map((w, i) => (
            <div key={i} className={`font-mono-t text-[11px] ${st.text}`}>→ {w}</div>
          ))}
        </div>
      </div>
    </div>
  );
};
