from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, async_session
from scheduler.jobs import start_scheduler, stop_scheduler
from api.games import router as games_router
from api.reports import router as reports_router
from api.dashboard import router as dashboard_router
from api.alerts import router as alerts_router
from api.qa import router as qa_router
from crawler.steam_community import crawl_all_games
from analyzer.llm_analyzer import analyze_all_games
from detector.anomaly_detector import detect_all_games
from notifier.slack_notifier import send_alert

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
    description="Steam 커뮤니티 유저 동향 분석 서비스",
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
app.include_router(alerts_router)
app.include_router(qa_router)


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


@app.post("/api/admin/trigger-detect", tags=["admin"])
async def trigger_detect(background_tasks: BackgroundTasks):
    """수동 이상 감지 트리거"""
    async def _run():
        async with async_session() as session:
            await detect_all_games(session)

    background_tasks.add_task(_run)
    return {"message": "이상 감지가 시작되었습니다."}


@app.post("/api/admin/trigger-notify/{alert_id}", tags=["admin"])
async def trigger_notify(alert_id: int, background_tasks: BackgroundTasks):
    """특정 Alert 수동 알림 재전송 트리거"""
    from sqlalchemy import select
    from models.alert import Alert as AlertModel
    from models.game import Game as GameModel

    async def _run():
        async with async_session() as session:
            alert_result = await session.execute(
                select(AlertModel).where(AlertModel.id == alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            if not alert:
                return
            game_result = await session.execute(
                select(GameModel).where(GameModel.id == alert.game_id)
            )
            game = game_result.scalar_one_or_none()
            if game:
                alert.notified = False  # 강제 재전송
                await send_alert(alert, game, session)

    background_tasks.add_task(_run)
    return {"message": f"Alert {alert_id} 알림 재전송이 시작되었습니다."}
