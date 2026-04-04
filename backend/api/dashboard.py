from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.game import Game
from models.report import Report
from schemas.report import DashboardSummaryItem

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/summary", response_model=list[DashboardSummaryItem])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    games_result = await db.execute(select(Game).where(Game.is_active == True))
    games = games_result.scalars().all()

    summary = []
    for game in games:
        report_result = await db.execute(
            select(Report)
            .where(Report.game_id == game.id)
            .where(Report.report_date == today)
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        summary.append(
            DashboardSummaryItem(
                game_id=game.id,
                game_name=game.name,
                thumbnail_url=game.thumbnail_url,
                summary=report.summary if report else None,
                sentiment=report.sentiment if report else None,
                top_keywords=report.trend_keywords[:5] if report and report.trend_keywords else None,
            )
        )
    return summary


@router.get("/compare", response_model=list[dict])
async def compare_games(
    game_ids: str,
    date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today()

    ids = [int(gid.strip()) for gid in game_ids.split(",") if gid.strip()]

    results = []
    for game_id in ids:
        game_result = await db.execute(select(Game).where(Game.id == game_id))
        game = game_result.scalar_one_or_none()
        if not game:
            continue
        report_result = await db.execute(
            select(Report)
            .where(Report.game_id == game_id)
            .where(Report.report_date == date)
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        results.append({
            "game_id": game.id,
            "game_name": game.name,
            "thumbnail_url": game.thumbnail_url,
            "report": {
                "summary": report.summary,
                "hot_topics": report.hot_topics,
                "sentiment": report.sentiment,
                "key_issues": report.key_issues,
                "trend_keywords": report.trend_keywords,
            } if report else None,
        })
    return results
