from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.report import Report
from schemas.report import ReportResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{game_id}", response_model=list[ReportResponse])
async def get_reports(
    game_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    result = await db.execute(
        select(Report)
        .where(Report.game_id == game_id)
        .where(Report.report_date >= start_date)
        .where(Report.report_date <= end_date)
        .order_by(Report.report_date.desc())
    )
    return result.scalars().all()


@router.get("/{game_id}/latest", response_model=ReportResponse)
async def get_latest_report(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report)
        .where(Report.game_id == game_id)
        .order_by(Report.report_date.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="리포트가 없습니다.")
    return report
