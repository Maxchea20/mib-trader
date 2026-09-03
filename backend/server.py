from fastapi import FastAPI, APIRouter, Query
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


app.include_router(api_router)

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
