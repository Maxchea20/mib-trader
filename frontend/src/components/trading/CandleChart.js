import React, { useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

const DIR = {
  support: "#00f59b",
  resistance: "#ff3b56",
  fibonacci: "#a855f7",
  breakout: "#38bdf8",
  dynamic: "#eab308",
};

export const CandleChart = ({ candles, levels = [], fvgZones = [], timeframe }) => {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volSeriesRef = useRef(null);
  const priceLinesRef = useRef([]);

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
  }, [candles]);

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

  return (
    <div className="relative w-full h-full" data-testid="trading-chart-container">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
};
