from datetime import date, datetime
from pydantic import BaseModel


class ReportBase(BaseModel):
    game_id: int
    report_date: date
    summary: str | None = None
    hot_topics: list | None = None
    sentiment: dict | None = None
    key_issues: dict | None = None
    trend_keywords: list | None = None
    raw_post_count: int = 0


class ReportCreate(ReportBase):
    pass


class ReportResponse(ReportBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardSummaryItem(BaseModel):
    game_id: int
    game_name: str
    thumbnail_url: str | None = None
    summary: str | None = None
    sentiment: dict | None = None
    top_keywords: list | None = None
