from datetime import datetime, date
from sqlalchemy import Integer, Text, Date, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("game_id", "report_date", name="uq_game_report_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    hot_topics: Mapped[dict | None] = mapped_column(JSON)
    sentiment: Mapped[dict | None] = mapped_column(JSON)
    key_issues: Mapped[dict | None] = mapped_column(JSON)
    trend_keywords: Mapped[dict | None] = mapped_column(JSON)
    raw_post_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
