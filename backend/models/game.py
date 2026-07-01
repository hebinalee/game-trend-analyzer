from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        # platform + app_id 복합 unique (steam=Steam App ID, mobile=Play Store 패키지명)
        UniqueConstraint("platform", "app_id", name="uq_platform_app_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="steam", index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    app_id: Mapped[str] = mapped_column(String(100), nullable=False)   # steam=App ID, mobile=Play Store 패키지명
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 모바일 게임 소스별 식별자 (nullable — steam 게임은 미사용)
    reddit_id: Mapped[str | None] = mapped_column(String(100))          # subreddit 이름
    play_store_id: Mapped[str | None] = mapped_column(String(150))      # Google Play 패키지명
    app_store_id: Mapped[str | None] = mapped_column(String(50))        # App Store 앱 ID
