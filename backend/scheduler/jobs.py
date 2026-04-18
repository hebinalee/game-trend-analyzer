"""
APScheduler 기반 스케줄 작업 정의

- crawl_job: 매 CRAWL_INTERVAL_HOURS 시간마다 전체 크롤링
- analyze_job: 매일 오전 7시 (KST, UTC+9) 분석 실행
- initial_crawl: 앱 시작 60초 후 즉시 1회 크롤링
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from database import async_session
from crawler.steam_community import crawl_all_games
from analyzer.llm_analyzer import analyze_all_games
from detector.anomaly_detector import detect_all_games
from notifier.slack_notifier import retry_failed_notifications

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _crawl_task():
    async with async_session() as session:
        logger.info("스케줄 크롤링 시작")
        await crawl_all_games(session)
        logger.info("스케줄 크롤링 완료")

    # 크롤링 완료 후 즉시 이상 감지 실행
    async with async_session() as session:
        logger.info("이상 감지 시작")
        alerts = await detect_all_games(session)
        logger.info(f"이상 감지 완료: {len(alerts)}개 Alert 생성")


async def _analyze_task():
    async with async_session() as session:
        logger.info("스케줄 분석 시작")
        await analyze_all_games(session)
        logger.info("스케줄 분석 완료")


async def _initial_crawl():
    await asyncio.sleep(60)
    await _crawl_task()


async def _retry_notify_task():
    async with async_session() as session:
        await retry_failed_notifications(session)


def start_scheduler():
    # 크롤링: 매 N시간
    scheduler.add_job(
        _crawl_task,
        trigger=IntervalTrigger(hours=settings.crawl_interval_hours),
        id="crawl_job",
        replace_existing=True,
    )

    # 분석: 매일 오전 7시 KST
    scheduler.add_job(
        _analyze_task,
        trigger=CronTrigger(hour=7, minute=0, timezone="Asia/Seoul"),
        id="analyze_job",
        replace_existing=True,
    )

    # 미전송 알림 재시도: 매 1시간
    scheduler.add_job(
        _retry_notify_task,
        trigger=IntervalTrigger(hours=1),
        id="retry_notify_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("스케줄러 시작됨")

    # 앱 시작 60초 후 즉시 크롤링 (일회성)
    asyncio.ensure_future(_initial_crawl())


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료됨")
