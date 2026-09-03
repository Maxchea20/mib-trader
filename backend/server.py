from fastapi import FastAPI, APIRouter, Query, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from src.config import (SYMBOL, TIMEFRAMES, AGENT_WEIGHTS, HTF_GATE, CONFLUENCE,
                        CONFLICT, ENTRY, CONFIG_VERSION, ASSUMPTIONS, HTF_TIMEFRAMES,
                        LTF_TIMEFRAMES)
from src.market_data import data_access as dao
from src.market_data import gap_sync, manager
from src import analysis_service
from src import settings as runtime_settings
from src import backtest as backtest_engine
from src import paper_trading
from src import autotrader
from pydantic import BaseModel
from typing import Optional, Dict

app = FastAPI(title="MIB-Trader API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mib-trader")


@api_router.get("/")
async def root():
    return {"app": "MIB-Trader", "version": CONFIG_VERSION, "symbol": SYMBOL,
            "timeframes": TIMEFRAMES}


@api_router.get("/config")
async def get_config():
    return {
        "config_version": CONFIG_VERSION,
        "symbol": SYMBOL,
        "timeframes": TIMEFRAMES,
        "htf_timeframes": HTF_TIMEFRAMES,
        "ltf_timeframes": LTF_TIMEFRAMES,
        "agent_weights": AGENT_WEIGHTS,
        "htf_gate": HTF_GATE,
        "confluence": CONFLUENCE,
        "conflict": CONFLICT,
        "entry": ENTRY,
        "assumptions": ASSUMPTIONS,
    }


# --- Market data (infrastructure) ---------------------------------------
@api_router.get("/market/ticker")
async def market_ticker():
    return manager.live_status()


@api_router.get("/market/candles")
async def market_candles(timeframe: str = Query("15m"), limit: int = Query(500)):
    if timeframe not in TIMEFRAMES:
        return {"error": "invalid_timeframe", "timeframes": TIMEFRAMES}
    candles = dao.read_candles(timeframe, limit=limit)
    live = manager.live_status()
    return {"symbol": SYMBOL, "timeframe": timeframe, "count": len(candles),
            "candles": candles, "live": live}


@api_router.get("/market/sync-status")
async def market_sync_status():
    status = dao.read_sync_status()
    for tf, info in status["timeframes"].items():
        info["gaps"] = len(gap_sync.detect_gaps(SYMBOL, tf))
    status["live"] = manager.live_status()
    return status


@api_router.post("/market/sync")
async def market_sync(timeframe: str = Query(...)):
    if timeframe not in TIMEFRAMES:
        return {"error": "invalid_timeframe"}
    return await gap_sync.sync_timeframe(SYMBOL, timeframe, limit=1000)


@api_router.get("/market/gaps")
async def market_gaps(timeframe: str = Query("15m")):
    if timeframe not in TIMEFRAMES:
        return {"error": "invalid_timeframe"}
    return {"timeframe": timeframe, "gaps": gap_sync.detect_gaps(SYMBOL, timeframe)}


# --- Analysis (10 agents + Brain) ---------------------------------------
@api_router.get("/analysis")
async def analysis(timeframe: str = Query("15m")):
    if timeframe not in TIMEFRAMES:
        return {"error": "invalid_timeframe", "timeframes": TIMEFRAMES}
    return analysis_service.full_analysis(timeframe)


@api_router.get("/agents/{agent_id}")
async def agent_detail(agent_id: str, timeframe: str = Query("15m")):
    return analysis_service.single_agent(agent_id, timeframe)


# --- Live config tuning --------------------------------------------------
class SettingsUpdate(BaseModel):
    agent_weights: Optional[Dict[str, float]] = None
    htf_gate: Optional[Dict[str, float]] = None
    confluence: Optional[Dict[str, float]] = None
    conflict: Optional[Dict[str, float]] = None
    entry: Optional[Dict[str, float]] = None


@api_router.get("/settings")
async def get_settings():
    return runtime_settings.snapshot()


@api_router.put("/settings")
async def put_settings(payload: SettingsUpdate):
    return runtime_settings.update(payload.model_dump(exclude_none=True))


@api_router.post("/settings/reset")
async def reset_settings():
    return runtime_settings.reset()


# --- Backtesting ---------------------------------------------------------
@api_router.get("/backtest")
async def backtest(timeframe: str = Query("15m"), lookback: int = Query(150),
                   forward: int = Query(8), step: int = Query(3)):
    if timeframe not in TIMEFRAMES:
        return {"error": "invalid_timeframe", "timeframes": TIMEFRAMES}
    import asyncio
    return await asyncio.to_thread(backtest_engine.run_backtest, timeframe,
                                   lookback, forward, step)


# --- Paper trading -------------------------------------------------------
class OpenTradeReq(BaseModel):
    side: str
    entry_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    notional_usd: float = 1000.0
    timeframe: str = ""
    brain_state: str = ""
    consensus: float = 0.0
    confidence: float = 0.0
    note: str = ""


class CloseTradeReq(BaseModel):
    exit_price: Optional[float] = None


@api_router.post("/paper/open")
async def paper_open(req: OpenTradeReq):
    live = manager.live_status()
    entry = req.entry_price if req.entry_price else live.get("last_price")
    if not entry:
        return {"error": "no_price_available"}
    return paper_trading.open_trade(
        symbol=SYMBOL, side=req.side, entry_price=entry, sl_price=req.sl_price,
        tp_price=req.tp_price, notional_usd=req.notional_usd, timeframe=req.timeframe,
        brain_state=req.brain_state, consensus=req.consensus, confidence=req.confidence,
        note=req.note,
    )


@api_router.post("/paper/close/{trade_id}")
async def paper_close(trade_id: str, req: CloseTradeReq):
    live = manager.live_status()
    exit_price = req.exit_price if req.exit_price else live.get("last_price")
    if not exit_price:
        return {"error": "no_price_available"}
    t = paper_trading.close_trade(trade_id, exit_price, "MANUAL")
    if not t:
        return {"error": "trade_not_found"}
    return t


@api_router.get("/paper/trades")
async def paper_trades(status: Optional[str] = Query(None)):
    live = manager.live_status()
    return {"trades": paper_trading.list_trades(status, live.get("last_price")),
            "live_price": live.get("last_price")}


@api_router.get("/paper/stats")
async def paper_stats():
    return paper_trading.stats()


# --- Auto-trader ---------------------------------------------------------
class AutoTradeReq(BaseModel):
    enabled: Optional[bool] = None
    timeframe: Optional[str] = None
    notional_usd: Optional[float] = None
    sl_atr_mult: Optional[float] = None
    tp_atr_mult: Optional[float] = None


@api_router.get("/autotrade")
async def autotrade_status():
    return autotrader.status()


@api_router.put("/autotrade")
async def autotrade_update(req: AutoTradeReq):
    return autotrader.update(req.model_dump(exclude_none=True))


app.include_router(api_router)


@app.websocket("/api/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    await manager.register(ws)
    try:
        # send an immediate snapshot so the client shows a price instantly
        await ws.send_text(manager._snapshot_msg())
        while True:
            # keep the connection open; ignore any inbound messages
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.unregister(ws)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("MIB-Trader starting — live-first market data")
    await manager.initial_load()
