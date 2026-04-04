from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, async_session
from scheduler.jobs import start_scheduler, stop_scheduler
from api.games import router as games_router
from api.reports import router as reports_router
from api.dashboard import router as dashboard_router
from crawler.naver_lounge import crawl_all_games
from analyzer.llm_analyzer import analyze_all_games

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Game Trend Analyzer API",
    description="네이버 게임 라운지 유저 동향 분석 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games_router)
app.include_router(reports_router)
app.include_router(dashboard_router)


@app.post("/api/admin/trigger-crawl", tags=["admin"])
async def trigger_crawl(background_tasks: BackgroundTasks):
    """수동 크롤링 트리거"""
    async def _run():
        async with async_session() as session:
            await crawl_all_games(session)

    background_tasks.add_task(_run)
    return {"message": "크롤링이 시작되었습니다."}


@app.post("/api/admin/trigger-analyze", tags=["admin"])
async def trigger_analyze(background_tasks: BackgroundTasks):
    """수동 분석 트리거"""
    async def _run():
        async with async_session() as session:
            await analyze_all_games(session)

    background_tasks.add_task(_run)
    return {"message": "분석이 시작되었습니다."}
