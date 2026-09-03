import React, { useEffect, useRef, useState } from "react";
import { createChart } from "lightweight-charts";

const DIR = {
  support: "#00f59b",
  resistance: "#ff3b56",
  fibonacci: "#a855f7",
  breakout: "#38bdf8",
  dynamic: "#eab308",
};

export const CandleChart = ({ candles, levels = [], fvgZones = [], confluenceZones = [], livePrice = null, timeframe }) => {
  const containerRef = useRef(null);
  const overlayRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volSeriesRef = useRef(null);
  const priceLinesRef = useRef([]);
  const lastCandleRef = useRef(null);
  const [bands, setBands] = useState([]);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      localization: { locale: "en-US" },
      layout: {
        background: { color: "#0d121b" },
        textColor: "#7d8ca3",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "rgba(45,58,80,0.25)" },
        horzLines: { color: "rgba(45,58,80,0.25)" },
      },
      rightPriceScale: { borderColor: "#1d2635" },
      timeScale: { borderColor: "#1d2635", timeVisible: true, secondsVisible: false },
      crosshair: {
        mode: 0,
        vertLine: { color: "#38bdf8", width: 1, style: 3, labelBackgroundColor: "#0f6fb3" },
        horzLine: { color: "#38bdf8", width: 1, style: 3, labelBackgroundColor: "#0f6fb3" },
      },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00f59b",
      downColor: "#ff3b56",
      borderUpColor: "#00f59b",
      borderDownColor: "#ff3b56",
      wickUpColor: "#00c88a",
      wickDownColor: "#e0304a",
    });
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volSeriesRef.current = volSeries;

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth, height: containerRef.current.clientHeight });
    });
    ro.observe(containerRef.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, []);

  useEffect(() => {
    if (!candleSeriesRef.current || !candles?.length) return;
    const cData = candles.map((c) => ({
      time: c.ts, open: c.open, high: c.high, low: c.low, close: c.close,
    }));
    const vData = candles.map((c) => ({
      time: c.ts, value: c.volume,
      color: c.close >= c.open ? "rgba(0,245,155,0.35)" : "rgba(255,59,86,0.35)",
    }));
    candleSeriesRef.current.setData(cData);
    volSeriesRef.current.setData(vData);
    lastCandleRef.current = cData.length ? { ...cData[cData.length - 1] } : null;
  }, [candles]);

  // live forming-candle update from the WS price feed
  useEffect(() => {
    const series = candleSeriesRef.current;
    const last = lastCandleRef.current;
    if (!series || !last || livePrice == null) return;
    const updated = {
      time: last.time,
      open: last.open,
      high: Math.max(last.high, livePrice),
      low: Math.min(last.low, livePrice),
      close: livePrice,
    };
    lastCandleRef.current = updated;
    try { series.update(updated); } catch (e) {}
  }, [livePrice]);

  // draw level price lines
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    priceLinesRef.current.forEach((pl) => {
      try { candleSeriesRef.current.removePriceLine(pl); } catch (e) {}
    });
    priceLinesRef.current = [];
    levels.slice(0, 10).forEach((lv) => {
      const line = candleSeriesRef.current.createPriceLine({
        price: lv.price,
        color: DIR[lv.type] || "#64748b",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: lv.label?.slice(0, 16) || "",
      });
      priceLinesRef.current.push(line);
    });
  }, [levels]);

  // FVG + confluence shaded bands via priceToCoordinate
  useEffect(() => {
    const compute = () => {
      const series = candleSeriesRef.current;
      const cont = containerRef.current;
      if (!series || !cont) return;
      const h = cont.clientHeight;
      const out = [];
      const push = (lo, hi, color, borderColor, label, key) => {
        if (lo == null || hi == null) return;
        let yTop = series.priceToCoordinate(Math.max(lo, hi));
        let yBot = series.priceToCoordinate(Math.min(lo, hi));
        if (yTop == null || yBot == null) return;
        yTop = Math.max(0, yTop);
        yBot = Math.min(h, yBot);
        const height = Math.max(2, yBot - yTop);
        if (yTop > h || yBot < 0) return;
        out.push({ key, top: yTop, height, color, borderColor, label });
      };
      (fvgZones || []).forEach((z, i) => {
        const bull = z.type === "fvg_bullish";
        push(z.low, z.high,
          bull ? "rgba(16,185,129,0.16)" : "rgba(244,63,94,0.16)",
          bull ? "rgba(16,185,129,0.5)" : "rgba(244,63,94,0.5)",
          `FVG ${bull ? "▲" : "▼"}${z.mitigated ? " ~" : ""}`, `fvg-${i}`);
      });
      (confluenceZones || []).forEach((z, i) => {
        push(z.low, z.high, "rgba(56,189,248,0.14)", "rgba(56,189,248,0.55)",
          `Confluence ×${z.count}`, `cf-${i}`);
      });
      setBands(out);
    };
    compute();
    const chart = chartRef.current;
    let unsub = () => {};
    if (chart) {
      const handler = () => compute();
      chart.timeScale().subscribeVisibleLogicalRangeChange(handler);
      unsub = () => chart.timeScale().unsubscribeVisibleLogicalRangeChange(handler);
    }
    const iv = setInterval(compute, 400);
    return () => { clearInterval(iv); unsub(); };
  }, [fvgZones, confluenceZones, candles]);

  return (
    <div className="relative w-full h-full" data-testid="trading-chart-container">
      <div ref={containerRef} className="w-full h-full" />
      <div ref={overlayRef} className="absolute inset-0 pointer-events-none" data-testid="chart-overlays">
        {bands.map((b) => (
          <div
            key={b.key}
            className="absolute left-0"
            style={{
              top: `${b.top}px`, height: `${b.height}px`, right: "58px",
              background: b.color, borderTop: `1px solid ${b.borderColor}`,
              borderBottom: `1px solid ${b.borderColor}`,
            }}
          >
            <span className="absolute left-1 top-0 font-mono-t text-[8px] leading-none px-1 py-0.5"
              style={{ color: b.borderColor }}>
              {b.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
