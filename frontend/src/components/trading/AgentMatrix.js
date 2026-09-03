import React, { useState } from "react";
import { AgentCard } from "./AgentCard";
import { AGENT_ORDER, AGENT_META } from "../../lib/api";
import { dirStyle, fmt } from "../../lib/style";
import { X, Filter } from "lucide-react";

const AgentDetailModal = ({ agent, onClose }) => {
  if (!agent) return null;
  const meta = AGENT_META[agent.agent] || {};
  const st = dirStyle(agent.direction);
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="panel max-w-lg w-full p-5 fade-up"
        style={{ boxShadow: st.glow }}
        onClick={(e) => e.stopPropagation()}
        data-testid="agent-detail-modal"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="widget-label">Agent {meta.num}</div>
            <div className="font-head font-bold text-2xl text-white">{meta.name}</div>
            <div className="font-mono-t text-[10px] text-slate-500">{meta.focus}</div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="panel p-2">
            <div className="widget-label">Direction</div>
            <div className={`font-head font-bold text-lg ${st.text}`}>{agent.direction}</div>
          </div>
          <div className="panel p-2">
            <div className="widget-label">Confidence</div>
            <div className="font-mono-t font-bold text-lg text-slate-100">{fmt(agent.confidence, 0)}%</div>
          </div>
          <div className="panel p-2">
            <div className="widget-label">Strength</div>
            <div className="font-mono-t font-bold text-lg text-cyan-400">{fmt(agent.strength, 0)}</div>
          </div>
        </div>

        <div className="mt-4">
          <div className="widget-label mb-1.5">Evidence</div>
          <div className="space-y-1">
            {(agent.evidence || []).map((e, i) => (
              <div key={i} className="font-mono-t text-[11px] text-slate-300 flex gap-2">
                <span className="text-slate-600">·</span>{e}
              </div>
            ))}
          </div>
        </div>

        {agent.key_levels?.length > 0 && (
          <div className="mt-4">
            <div className="widget-label mb-1.5">Key Levels</div>
            <div className="flex flex-wrap gap-1.5">
              {agent.key_levels.map((lv, i) => (
                <span key={i} className="font-mono-t text-[10px] px-2 py-1 rounded-sm bg-[#151b24] border border-[#1d2635] text-slate-300">
                  {lv.label}: ${fmt(lv.price, 1)}
                </span>
              ))}
            </div>
          </div>
        )}
        <div className="mt-3 font-mono-t text-[10px] text-slate-500">
          timeframe {agent.timeframe} · valid: {String(agent.valid)}
        </div>
      </div>
    </div>
  );
};

export const AgentMatrix = ({ agents = [], hoveredType }) => {
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("ALL");

  const byId = Object.fromEntries(agents.map((a) => [a.agent, a]));
  const ordered = AGENT_ORDER.map((id) => byId[id]).filter(Boolean);
  const shown = filter === "ALL" ? ordered : ordered.filter((a) => a.direction === filter);

  return (
    <div data-testid="agent-matrix">
      <div className="flex items-center justify-between mb-2 px-0.5">
        <div className="flex items-center gap-2">
          <span className="font-head font-bold text-slate-200 tracking-wide text-lg">10 INDEPENDENT TA AGENTS</span>
          <span className="widget-label">Layer 3</span>
        </div>
        <div className="flex items-center gap-1">
          <Filter className="w-3 h-3 text-slate-500" />
          {["ALL", "LONG", "SHORT", "NEUTRAL"].map((f) => (
            <button
              key={f}
              data-testid={`agent-filter-${f.toLowerCase()}`}
              onClick={() => setFilter(f)}
              className={`font-mono-t text-[10px] px-2 py-0.5 rounded-sm transition-colors ${
                filter === f ? "bg-[#1f2a3d] text-white" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
        {shown.map((a, i) => (
          <AgentCard
            key={a.agent}
            agent={a}
            index={i}
            onClick={setSelected}
            highlight={hoveredType && a.key_levels?.some((l) => l.type?.includes(hoveredType))}
          />
        ))}
      </div>

      <AgentDetailModal agent={selected} onClose={() => setSelected(null)} />
    </div>
  );
};
