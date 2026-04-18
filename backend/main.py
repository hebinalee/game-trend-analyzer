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
from crawler.steam_community import crawl_all_games
from analyzer.llm_analyzer import analyze_all_games
from detector.anomaly_detector import detect_all_games
from notifier.slack_notifier import send_alert
from storage.db_sync import sync_date_to_db, sync_all_to_db
from storage.file_store import data_summary

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


@app.get("/api/admin/data-summary", tags=["admin"])
async def get_data_summary():
    """로컬 파일 저장 현황 조회."""
    return data_summary()


@app.post("/api/admin/trigger-sync", tags=["admin"])
async def trigger_sync(background_tasks: BackgroundTasks, target_date: str | None = None):
    """파일 → DB 동기화 트리거. target_date 미지정 시 오늘 날짜."""
    from datetime import date

    async def _run():
        async with async_session() as session:
            if target_date:
                d = date.fromisoformat(target_date)
                await sync_date_to_db(session, d)
            else:
                await sync_date_to_db(session, date.today())

    background_tasks.add_task(_run)
    return {"message": f"DB 동기화가 시작되었습니다. (날짜: {target_date or '오늘'})"}


@app.post("/api/admin/trigger-sync-all", tags=["admin"])
async def trigger_sync_all(background_tasks: BackgroundTasks):
    """로컬에 저장된 모든 날짜 데이터를 DB에 동기화."""
    async def _run():
        async with async_session() as session:
            await sync_all_to_db(session)

    background_tasks.add_task(_run)
    return {"message": "전체 DB 동기화가 시작되었습니다."}


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
