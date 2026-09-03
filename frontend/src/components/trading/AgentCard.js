import React from "react";
import { motion } from "framer-motion";
import { AGENT_META } from "../../lib/api";
import { dirStyle, fmt } from "../../lib/style";

export const AgentCard = ({ agent, onClick, index, highlight }) => {
  const meta = AGENT_META[agent.agent] || { name: agent.agent, focus: "", num: "" };
  const st = dirStyle(agent.direction);
  return (
    <motion.button
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      onClick={() => onClick(agent)}
      data-testid={`agent-card-${agent.agent}`}
      className={`panel panel-hover text-left p-3 flex flex-col gap-2 ${
        !agent.valid ? "opacity-55" : ""
      } ${highlight ? "border-cyan-500/70" : ""}`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-mono-t text-[9px] text-slate-600">{meta.num}</span>
            <span className="font-head font-semibold text-[13px] text-slate-100 truncate">{meta.name}</span>
          </div>
          <div className="font-mono-t text-[9px] text-slate-500 mt-0.5 truncate">{meta.focus}</div>
        </div>
        <span className={`font-mono-t text-[10px] font-bold px-1.5 py-0.5 rounded-sm border ${st.bg} ${st.border} ${st.text}`}>
          {agent.direction}
        </span>
      </div>

      <div className="flex items-end justify-between gap-2">
        <div className="flex-1">
          <div className="flex justify-between items-baseline">
            <span className="widget-label">Conf</span>
            <span className="font-mono-t text-xs font-bold text-slate-200">{fmt(agent.confidence, 0)}%</span>
          </div>
          <div className="h-1 bar-track mt-1">
            <div className="h-full" style={{ width: `${agent.confidence}%`, background: st.raw === "none" ? "#64748b" : st.raw }} />
          </div>
        </div>
        <div className="w-14">
          <div className="widget-label text-right">Str</div>
          <div className="h-1 bar-track mt-1">
            <div className="h-full" style={{ width: `${agent.strength}%`, background: "#38bdf8" }} />
          </div>
        </div>
      </div>

      {!agent.valid && <div className="font-mono-t text-[9px] text-amber-500/80">low reliability</div>}
    </motion.button>
  );
};
