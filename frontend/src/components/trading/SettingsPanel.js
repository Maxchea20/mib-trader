import React, { useEffect, useState, useRef } from "react";
import { X, RotateCcw, SlidersHorizontal } from "lucide-react";
import { getSettings, updateSettings, resetSettings, AGENT_META } from "../../lib/api";

const WEIGHT_MAX = 3;

const Slider = ({ label, value, min, max, step, onChange, unit }) => (
  <div className="mb-2.5">
    <div className="flex justify-between items-baseline mb-1">
      <span className="font-mono-t text-[11px] text-slate-300">{label}</span>
      <span className="font-mono-t text-[11px] font-bold text-cyan-400">{Number(value).toFixed(step < 1 ? 2 : 0)}{unit || ""}</span>
    </div>
    <input
      type="range" min={min} max={max} step={step} value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full accent-cyan-500 h-1 cursor-pointer"
    />
  </div>
);

const Section = ({ title, children }) => (
  <div className="mb-5">
    <div className="widget-label mb-2 pb-1 border-b border-[#1d2635]">{title}</div>
    {children}
  </div>
);

export const SettingsPanel = ({ open, onClose, onChanged }) => {
  const [s, setS] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    if (open) getSettings().then(setS).catch(() => {});
  }, [open]);

  const pushUpdate = (next) => {
    setS(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      await updateSettings({
        agent_weights: next.agent_weights,
        htf_gate: next.htf_gate,
        conflict: next.conflict,
        entry: next.entry,
      });
      onChanged?.();
    }, 350);
  };

  const setW = (id, v) => pushUpdate({ ...s, agent_weights: { ...s.agent_weights, [id]: v } });
  const setSec = (sec, k, v) => pushUpdate({ ...s, [sec]: { ...s[sec], [k]: v } });

  const doReset = async () => {
    const fresh = await resetSettings();
    setS(fresh);
    onChanged?.();
  };

  return (
    <>
      {open && <div className="fixed inset-0 z-[55] bg-black/50" onClick={onClose} />}
      <div
        data-testid="settings-panel"
        className={`fixed top-0 right-0 h-full w-[380px] z-[56] bg-[#0b0f16] border-l border-[#1d2635] transition-transform duration-300 overflow-y-auto ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="sticky top-0 bg-[#0b0f16] z-10 flex items-center justify-between px-4 h-14 border-b border-[#1d2635]">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-cyan-400" />
            <span className="font-head font-bold text-lg text-white tracking-wide">CONFIG · V1 TUNING</span>
          </div>
          <button onClick={onClose} data-testid="settings-close" className="text-slate-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {!s ? (
          <div className="p-4 widget-label">Loading…</div>
        ) : (
          <div className="p-4">
            <button
              onClick={doReset}
              data-testid="settings-reset"
              className="flex items-center gap-1.5 font-mono-t text-[11px] text-amber-400 mb-4 px-2 py-1 rounded-sm border border-amber-500/30 hover:bg-amber-500/10"
            >
              <RotateCcw className="w-3 h-3" /> Reset to V1 defaults
            </button>

            <Section title="Agent Weights">
              {Object.keys(s.agent_weights).map((id) => (
                <Slider
                  key={id}
                  label={AGENT_META[id]?.name || id}
                  value={s.agent_weights[id]}
                  min={0} max={WEIGHT_MAX} step={0.1}
                  onChange={(v) => setW(id, v)}
                />
              ))}
            </Section>

            <Section title="HTF Regime Gate">
              <Slider label="Regime min score" value={s.htf_gate.regime_min_score} min={0} max={60} step={1} onChange={(v) => setSec("htf_gate", "regime_min_score", v)} />
              <Slider label="Counter-trend penalty" value={s.htf_gate.counter_trend_penalty} min={0} max={60} step={1} onChange={(v) => setSec("htf_gate", "counter_trend_penalty", v)} />
              <Slider label="Counter-trend conf penalty" value={s.htf_gate.counter_trend_confidence_penalty} min={0} max={40} step={1} onChange={(v) => setSec("htf_gate", "counter_trend_confidence_penalty", v)} />
              <Slider label="Aligned bonus" value={s.htf_gate.aligned_bonus} min={0} max={30} step={1} onChange={(v) => setSec("htf_gate", "aligned_bonus", v)} />
            </Section>

            <Section title="Conflict / Contradiction">
              <Slider label="Strong confidence" value={s.conflict.strong_confidence} min={40} max={95} step={1} unit="%" onChange={(v) => setSec("conflict", "strong_confidence", v)} />
              <Slider label="Min opposing agents" value={s.conflict.contradiction_min_agents} min={1} max={5} step={1} onChange={(v) => setSec("conflict", "contradiction_min_agents", v)} />
              <Slider label="Severe ratio" value={s.conflict.severe_ratio} min={0.5} max={1} step={0.01} onChange={(v) => setSec("conflict", "severe_ratio", v)} />
              <Slider label="Veto ratio" value={s.conflict.veto_ratio} min={0.6} max={1} step={0.01} onChange={(v) => setSec("conflict", "veto_ratio", v)} />
              <Slider label="Confidence penalty" value={s.conflict.confidence_penalty} min={0} max={40} step={1} onChange={(v) => setSec("conflict", "confidence_penalty", v)} />
            </Section>

            <Section title="Entry Thresholds">
              <Slider label="Direction min score" value={s.entry.direction_min_score} min={0} max={60} step={1} onChange={(v) => setSec("entry", "direction_min_score", v)} />
              <Slider label="Entry min score" value={s.entry.entry_min_score} min={0} max={90} step={1} onChange={(v) => setSec("entry", "entry_min_score", v)} />
              <Slider label="Entry min confidence" value={s.entry.entry_min_confidence} min={0} max={95} step={1} unit="%" onChange={(v) => setSec("entry", "entry_min_confidence", v)} />
              <Slider label="Min valid agents" value={s.entry.min_valid_agents} min={1} max={10} step={1} onChange={(v) => setSec("entry", "min_valid_agents", v)} />
            </Section>

            <div className="font-mono-t text-[9px] text-slate-600 leading-relaxed">
              Changes apply instantly to the Brain decision. These are V1 assumptions, not calibrated values.
            </div>
          </div>
        )}
      </div>
    </>
  );
};
