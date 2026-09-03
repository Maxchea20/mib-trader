import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

const client = axios.create({ baseURL: API, timeout: 20000 });

export const getTicker = async () => (await client.get("/market/ticker")).data;
export const getCandles = async (tf, limit = 500) =>
  (await client.get("/market/candles", { params: { timeframe: tf, limit } })).data;
export const getSyncStatus = async () => (await client.get("/market/sync-status")).data;
export const getAnalysis = async (tf) =>
  (await client.get("/analysis", { params: { timeframe: tf } })).data;
export const getConfig = async () => (await client.get("/config")).data;
export const getSettings = async () => (await client.get("/settings")).data;
export const updateSettings = async (payload) => (await client.put("/settings", payload)).data;
export const resetSettings = async () => (await client.post("/settings/reset")).data;
export const runBacktest = async ({ timeframe, lookback = 150, forward = 8, step = 3 }) =>
  (await client.get("/backtest", { params: { timeframe, lookback, forward, step } })).data;

export const openPaperTrade = async (payload) => (await client.post("/paper/open", payload)).data;
export const closePaperTrade = async (id) => (await client.post(`/paper/close/${id}`, {})).data;
export const getPaperTrades = async (status) =>
  (await client.get("/paper/trades", { params: status ? { status } : {} })).data;
export const getPaperStats = async () => (await client.get("/paper/stats")).data;
export const getAutotrade = async () => (await client.get("/autotrade")).data;
export const updateAutotrade = async (payload) => (await client.put("/autotrade", payload)).data;

export const AGENT_META = {
  market_structure: { name: "Market Structure", focus: "HH / HL / LH / LL · BOS · CHoCH", num: "01" },
  breakout: { name: "Breakout / Breakdown", focus: "Range · Volume · ATR · Follow-through", num: "02" },
  fibonacci: { name: "Fibonacci", focus: "Retracement · Golden Pocket · Ext", num: "03" },
  elliott_wave: { name: "Elliott Wave", focus: "Motive 1-5 · Corrective A-B-C", num: "04" },
  volume: { name: "Volume", focus: "RVOL · Expansion · Participation", num: "05" },
  momentum: { name: "Momentum", focus: "RSI · MACD · ROC · EMA slope", num: "06" },
  support_resistance: { name: "Support / Resistance", focus: "Clustered level zones", num: "07" },
  trend: { name: "Trend", focus: "EMA ribbon · Slope · Regime", num: "08" },
  pattern: { name: "Pattern Analysis", focus: "Flags · Triangles · Double top/bottom", num: "09" },
  fair_value_gap: { name: "Fair Value Gap", focus: "ICT imbalance · Mitigation", num: "10" },
};

export const AGENT_ORDER = Object.keys(AGENT_META);
