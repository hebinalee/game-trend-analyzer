from datetime import datetime
from pydantic import BaseModel


class PostBase(BaseModel):
    game_id: int
    post_id: str
    title: str | None = None
    content: str | None = None
    author: str | None = None
    like_count: int = 0
    comment_count: int = 0
    post_type: str | None = None
    posted_at: datetime | None = None


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    id: int
    crawled_at: datetime | None = None

    class Config:
        from_attributes = True
