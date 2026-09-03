import React from "react";
import { motion } from "framer-motion";
import { dirStyle, fmt } from "../../lib/style";

const ConsensusBar = ({ score }) => {
  // score -100..100, zero-centered
  const pct = Math.max(-100, Math.min(100, score || 0));
  const isPos = pct >= 0;
  const width = Math.abs(pct) / 2; // half-width max 50%
  return (
    <div className="mt-1">
      <div className="relative h-3 bar-track">
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-500/60 z-10" />
        <motion.div
          className="absolute top-0 bottom-0"
          style={{
            background: isPos ? "linear-gradient(90deg,rgba(0,245,155,0.4),#00f59b)" : "linear-gradient(270deg,rgba(255,59,86,0.4),#ff3b56)",
            left: isPos ? "50%" : `${50 - width}%`,
          }}
          initial={{ width: 0 }}
          animate={{ width: `${width}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <div className="flex justify-between font-mono-t text-[9px] text-slate-500 mt-0.5">
        <span>-100 BEAR</span>
        <span>0</span>
        <span>BULL +100</span>
      </div>
    </div>
  );
};

const Gauge = ({ label, value, color, testid }) => (
  <div>
    <div className="flex justify-between items-baseline">
      <span className="widget-label">{label}</span>
      <span className="font-mono-t text-sm font-bold" style={{ color }} data-testid={testid}>
        {fmt(value, 0)}{label.includes("CONF") ? "%" : ""}
      </span>
    </div>
    <div className="h-1.5 bar-track mt-1">
      <motion.div
        className="h-full rounded-sm"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, Math.abs(value))}%` }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      />
    </div>
  </div>
);

export const BrainHeroPanel = ({ brain }) => {
  if (!brain || brain.error) {
    return (
      <div className="panel p-4 h-full flex items-center justify-center" data-testid="brain-decision-hero">
        <span className="widget-label">Awaiting brain consensus…</span>
      </div>
    );
  }
  const st = dirStyle(brain.state);
  return (
    <div
      className={`panel ${st.border} p-4 relative overflow-hidden fade-up`}
      style={{ boxShadow: st.glow }}
      data-testid="brain-decision-hero"
    >
      <div className="flex items-center justify-between">
        <span className="widget-label">Brain Consensus Engine</span>
        <span className="widget-label">{brain.timeframe} · {brain.active_agents} agents</span>
      </div>

      <div className="flex items-end justify-between mt-2">
        <div>
          <motion.div
            key={brain.state}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`font-head font-black text-5xl leading-none tracking-tight ${st.text} ${brain.state === "LONG" || brain.state === "SHORT" ? "pulse-dot" : ""}`}
            data-testid="brain-decision-badge"
          >
            {brain.state}
          </motion.div>
          <div className="font-mono-t text-[11px] text-slate-400 mt-1">
            bias {brain.direction}
          </div>
        </div>
        <div className="text-right">
          <div className="widget-label">Consensus</div>
          <div
            className="font-mono-t font-bold text-3xl tabular-nums"
            style={{ color: brain.consensus_score >= 0 ? "#00f59b" : "#ff3b56" }}
            data-testid="brain-consensus-score"
          >
            {brain.consensus_score >= 0 ? "+" : ""}{fmt(brain.consensus_score, 0)}
          </div>
        </div>
      </div>

      <ConsensusBar score={brain.consensus_score} />

      <div className="grid grid-cols-2 gap-3 mt-4" data-testid="brain-confidence-gauge">
        <Gauge label="CONFIDENCE" value={brain.confidence} color={st.raw === "none" ? "#94a3b8" : st.raw} testid="brain-confidence-value" />
        <div>
          <div className="flex justify-between items-baseline">
            <span className="widget-label">Req · Score / Conf</span>
          </div>
          <div className="font-mono-t text-xs text-slate-300 mt-1.5">
            {fmt(brain.entry_score_required, 0)} / {fmt(brain.entry_confidence_required, 0)}%
          </div>
          <div className="font-mono-t text-[10px] text-slate-500 mt-0.5">
            HTF gate: {brain.htf_gate?.relation}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#1d2635] font-mono-t text-[10px]">
        <div>
          <div className="widget-label">Confluence</div>
          <div className="text-cyan-400 mt-0.5">+{fmt(brain.confluence_bonus, 1)}</div>
        </div>
        <div>
          <div className="widget-label">Conflict</div>
          <div className={`mt-0.5 ${brain.conflict?.severity === "none" ? "text-slate-400" : "text-amber-400"}`}>
            {brain.conflict?.severity} ({fmt((brain.conflict?.opposing_ratio || 0) * 100, 0)}%)
          </div>
        </div>
        <div>
          <div className="widget-label">HTF Regime</div>
          <div className={dirStyle(brain.htf_regime?.regime).text + " mt-0.5"}>
            {brain.htf_regime?.regime} {brain.htf_regime?.regime_score >= 0 ? "+" : ""}{fmt(brain.htf_regime?.regime_score, 0)}
          </div>
        </div>
      </div>
    </div>
  );
};
