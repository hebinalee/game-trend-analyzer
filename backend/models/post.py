from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    post_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="steam", index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[float | None] = mapped_column(Float)          # 1.0~5.0 (GooglePlay/AppStore), null (Steam/Reddit)
    like_count: Mapped[int | None] = mapped_column(Integer)      # Steam=helpful, Reddit=score, GooglePlay=thumbsUp, AppStore=null
    comment_count: Mapped[int | None] = mapped_column(Integer)   # Reddit=댓글수, 나머지=null
    post_type: Mapped[str | None] = mapped_column(String(50))
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
