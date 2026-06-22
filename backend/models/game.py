from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        # 같은 플랫폼 내에서 app_id 중복 방지 (플랫폼 간 동일 ID 허용)
        UniqueConstraint("platform", "app_id", name="uq_platform_app_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="steam", index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    app_id: Mapped[str] = mapped_column(String(50), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
