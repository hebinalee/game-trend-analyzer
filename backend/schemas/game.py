from pydantic import BaseModel


class GameBase(BaseModel):
    name: str
    lounge_id: str
    thumbnail_url: str | None = None


class GameCreate(GameBase):
    pass


class GameResponse(GameBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
