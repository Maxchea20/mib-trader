export const STATE_STYLE = {
  LONG: { text: "text-emerald-400", bg: "bg-emerald-950/50", border: "border-emerald-500/60", raw: "#00f59b", glow: "0 0 26px rgba(0,245,155,0.4)" },
  SHORT: { text: "text-rose-400", bg: "bg-rose-950/50", border: "border-rose-500/60", raw: "#ff3b56", glow: "0 0 26px rgba(255,59,86,0.4)" },
  WAIT: { text: "text-amber-400", bg: "bg-amber-950/40", border: "border-amber-500/60", raw: "#ffb800", glow: "0 0 26px rgba(255,184,0,0.35)" },
  AVOID: { text: "text-slate-300", bg: "bg-slate-800/50", border: "border-slate-500/50", raw: "#94a3b8", glow: "none" },
  NEUTRAL: { text: "text-slate-400", bg: "bg-slate-800/40", border: "border-slate-600/40", raw: "#94a3b8", glow: "none" },
};

export const dirStyle = (d) => STATE_STYLE[d] || STATE_STYLE.NEUTRAL;

export const fmt = (n, d = 1) =>
  n === null || n === undefined || isNaN(n)
    ? "—"
    : Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
