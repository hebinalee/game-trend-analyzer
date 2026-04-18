from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)    # CRITICAL / WARNING / INFO
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sentiment_drop / volume_spike / keyword_alert
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON)                    # 감지 수치 상세
    recommendations: Mapped[dict | None] = mapped_column(JSON)           # Agent C가 채움
    status: Mapped[str] = mapped_column(String(20), default="new")       # new / acknowledged / resolved
    notified: Mapped[bool] = mapped_column(Boolean, default=False)       # Slack 전송 여부
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
