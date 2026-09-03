# MIB-Trader — Product Requirements Document

## Original Problem Statement
Build MIB-Trader, a professional cryptocurrency trading-analysis application (web app adaptation of the Tauri desktop spec) built around persistent MEXC Futures market data, 10 independent technical-analysis agents, multi-timeframe analysis, and a final Brain consensus engine that outputs LONG / SHORT / WAIT / AVOID with a traceable, weighted-evidence decision. Analysis/decision-support only — no profitability claims, no fabricated results, all V1 formulas/thresholds exposed as configurable assumptions.

## User Choices
- Web app keeping exact architecture (FastAPI hosts persistent **SQLite** market DB; separate market_data module + 10 agent modules + Brain).
- MEXC Futures REST/WebSocket; graceful fallback to seeded/simulated candles if the region blocks MEXC.
- Config values backend-only (V1 assumptions in `src/config.py`).
- Full end-to-end first build.
- lightweight-charts (TradingView-style) candlesticks.

## Architecture
- **Backend** `/app/backend/src/`
  - `market_data/` (infra only): `database.py` (SQLite), `data_access.py` (read-only layer for agents), `mexc_market_data.py` (REST+ticker), `gap_sync.py` (gap detect/recovery), `manager.py` (live-first startup + poller + fallback).
  - Agent folders (one each): `structure`, `breakout`, `fibonacci`, `elliott_wave`, `volume`, `momentum`, `support_resistance`, `trend`, `pattern`, `fair_value_gap`. Each returns the `AgentResult` contract (`contract.py`).
  - `brain/`: `confluence.py` (Phase D), `conflict.py` (Phase E), `mtf.py` (Phase C HTF gate), `brain.py` (Phase G decision).
  - `analysis_service.py` orchestrates 10 agents + HTF regime + Brain; `indicators.py` shared TA math; `config.py` V1 params.
- **Frontend** `/app/frontend/src/`: `App.js` dashboard; `components/trading/*` (AppHeader, CandleChart, BrainHeroPanel, ExplainabilityPanel, AgentMatrix, AgentCard, MultiTimeframeRegime, KeyLevelsPanel); `lib/api.js`, `lib/style.js`.
- Persistent local SQLite at `/app/backend/market_data.db`. No cloud DB for market history. No auth.

## Core Requirements (static)
- MEXC Futures BTC_USDT, timeframes 1m/5m/15m/30m/1h/4h/1d.
- Live-first startup: serve live price + local candles immediately, sync/gap-fill in background.
- Exactly 10 agents, standardized output contract, no extra agents (no Whale/Sentiment/News/Liquidity).
- MTF: 4h/1d = HTF regime gate (not averaged into LTF score); counter-trend raises requirements.
- Brain uses weighted evidence + confluence dedup + conflict detection → LONG/SHORT/WAIT/AVOID with traceable reasons.

## Implemented (2026-06 — first build)
- Full market-data infrastructure (SQLite persistence, MEXC REST live sync ~1000 candles/TF, gap detection, poller, simulated fallback).
- All 10 TA agents with real deterministic logic + standardized contract.
- Brain engine: base consensus (Σ dir×conf×weight / Σweight), confluence with diminishing returns, conflict/veto detection, HTF gate, explicit LONG/SHORT/WAIT/AVOID resolution with traceable reasons + why_state.
- Endpoints: `/api/`, `/api/config`, `/api/market/{ticker,candles,sync-status,sync,gaps}`, `/api/analysis`, `/api/agents/{id}`.
- Professional dark tactical workstation UI (3 layers: Market Data / Brain / Agents), lightweight-charts with level overlays, agent detail modals, filters, HTF regime + confluence inspector.
- Verified: 100% backend (22/22 pytest) + 100% frontend.

## Backlog / Remaining
- **P1**: Backtesting engine + calibration/optimization of weights and thresholds (Phase after Brain).
- **P1**: True WebSocket push from backend for tick-level live candle (currently REST polling every ~4s).
- **P2**: Settings UI to tune V1 config live (currently backend-only by user choice).
- **P2**: Additional symbols beyond BTC_USDT.
- **P2**: Chart overlays for FVG shaded zones and confluence highlighting on hover.

## Next Tasks
- Add backtesting harness that replays SQLite history through the Brain.
- Persist/version config presets for calibration experiments.
