import { useEffect, useState, useCallback, useRef } from "react";
import "@/index.css";
import { RefreshCw } from "lucide-react";
import {
  getTicker, getCandles, getAnalysis, getSyncStatus,
} from "@/lib/api";
import { AppHeader } from "@/components/trading/AppHeader";
import { CandleChart } from "@/components/trading/CandleChart";
import { BrainHeroPanel } from "@/components/trading/BrainHeroPanel";
import { ExplainabilityPanel } from "@/components/trading/ExplainabilityPanel";
import { AgentMatrix } from "@/components/trading/AgentMatrix";
import { MultiTimeframeRegime } from "@/components/trading/MultiTimeframeRegime";
import { KeyLevelsPanel } from "@/components/trading/KeyLevelsPanel";

function App() {
  const [timeframe, setTimeframe] = useState("15m");
  const [ticker, setTicker] = useState(null);
  const [live, setLive] = useState(null);
  const [candles, setCandles] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [hoveredType, setHoveredType] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const tfRef = useRef(timeframe);
  tfRef.current = timeframe;

  const loadTicker = useCallback(async () => {
    try {
      const d = await getTicker();
      setLive(d);
      setTicker(d.ticker);
    } catch (e) {}
  }, []);

  const loadCandles = useCallback(async (tf) => {
    try {
      const d = await getCandles(tf, 500);
      if (tfRef.current === tf) setCandles(d.candles || []);
    } catch (e) {}
  }, []);

  const loadAnalysis = useCallback(async (tf) => {
    try {
      const d = await getAnalysis(tf);
      if (tfRef.current === tf) setAnalysis(d);
    } catch (e) {}
  }, []);

  const loadSync = useCallback(async () => {
    try { setSyncStatus(await getSyncStatus()); } catch (e) {}
  }, []);

  const refreshAll = useCallback(async (tf) => {
    setRefreshing(true);
    await Promise.all([loadCandles(tf), loadAnalysis(tf)]);
    setRefreshing(false);
  }, [loadCandles, loadAnalysis]);

  // on timeframe change
  useEffect(() => {
    setCandles([]);
    setAnalysis(null);
    refreshAll(timeframe);
  }, [timeframe, refreshAll]);

  // pollers
  useEffect(() => {
    loadTicker();
    loadSync();
    const t1 = setInterval(loadTicker, 3000);
    const t2 = setInterval(() => loadCandles(tfRef.current), 8000);
    const t3 = setInterval(() => loadAnalysis(tfRef.current), 12000);
    const t4 = setInterval(loadSync, 15000);
    return () => { [t1, t2, t3, t4].forEach(clearInterval); };
  }, [loadTicker, loadCandles, loadAnalysis, loadSync]);

  // chart levels from agents
  const levels = [];
  if (analysis?.agents) {
    const pull = (id) => analysis.agents.find((a) => a.agent === id)?.key_levels || [];
    pull("support_resistance").forEach((l) => levels.push(l));
    pull("fibonacci").slice(0, 4).forEach((l) => levels.push(l));
    pull("breakout").forEach((l) => levels.push(l));
    pull("trend").forEach((l) => levels.push(l));
  }

  return (
    <div className="min-h-screen scanlines" style={{ background: "#080b10" }}>
      <AppHeader
        ticker={ticker}
        live={live}
        timeframe={timeframe}
        onTimeframe={setTimeframe}
        syncStatus={syncStatus}
      />

      <main className="pt-16 px-3 pb-6 max-w-[1800px] mx-auto">
        <div className="grid grid-cols-12 gap-3">
          {/* LAYER 1 — market data (left) */}
          <section className="col-span-12 xl:col-span-8 flex flex-col gap-3">
            <div className="flex items-center justify-between px-0.5">
              <div className="flex items-center gap-2">
                <span className="font-head font-bold text-slate-200 tracking-wide text-lg">MARKET DATA</span>
                <span className="widget-label">Layer 1 · MEXC Futures · SQLite</span>
              </div>
              <button
                data-testid="refresh-analysis-button"
                onClick={() => refreshAll(timeframe)}
                className="flex items-center gap-1.5 font-mono-t text-[11px] text-slate-300 px-2.5 py-1 rounded-sm bg-[#0d121b] border border-[#1d2635] hover:border-cyan-500/60 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
                Recompute
              </button>
            </div>

            <div className="panel h-[420px]">
              {candles.length > 0 ? (
                <CandleChart candles={candles} levels={levels} timeframe={timeframe} />
              ) : (
                <div className="w-full h-full flex items-center justify-center widget-label">
                  Loading local candles…
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <MultiTimeframeRegime htf={analysis?.htf_regime} />
              <div className="lg:col-span-2">
                <KeyLevelsPanel analysis={analysis} onHover={setHoveredType} />
              </div>
            </div>
          </section>

          {/* LAYER 2 — brain (right) */}
          <section className="col-span-12 xl:col-span-4 flex flex-col gap-3">
            <div className="flex items-center gap-2 px-0.5">
              <span className="font-head font-bold text-slate-200 tracking-wide text-lg">BRAIN DECISION</span>
              <span className="widget-label">Layer 2 · Command</span>
            </div>
            <BrainHeroPanel brain={analysis?.brain} />
            <ExplainabilityPanel brain={analysis?.brain} />
          </section>
        </div>

        {/* LAYER 3 — agents */}
        <div className="mt-4">
          <AgentMatrix agents={analysis?.agents || []} hoveredType={hoveredType} />
        </div>

        <div className="mt-4 font-mono-t text-[10px] text-slate-600 leading-relaxed panel p-3">
          <span className="text-slate-400">V1 assumptions:</span>{" "}
          {(analysis?.brain?.assumptions || []).join("  ·  ")}
        </div>
      </main>
    </div>
  );
}

export default App;
