from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models.post import Post

router = APIRouter(prefix="/api/posts", tags=["posts"])


class PostResponse(BaseModel):
    id: int
    post_id: str
    source: str
    title: str | None = None
    content: str | None = None
    author: str | None = None
    like_count: int
    comment_count: int
    post_type: str | None = None
    posted_at: datetime | None = None
    crawled_at: datetime | None = None

    class Config:
        from_attributes = True


@router.get("/{game_id}", response_model=list[PostResponse])
async def get_posts(
    game_id: int,
    source: str | None = Query(default=None, description="'steam' 또는 'reddit'으로 필터"),
    days_back: int = Query(default=1, ge=1, le=30, description="최근 며칠치 게시글 (기본 1일)"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """게임별 최근 수집 게시글 조회. source 파라미터로 플랫폼 필터링 가능."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    query = (
        select(Post)
        .where(Post.game_id == game_id)
        .where(Post.crawled_at >= cutoff)
    )
    if source:
        query = query.where(Post.source == source)
    query = query.order_by(desc(Post.like_count + Post.comment_count)).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
