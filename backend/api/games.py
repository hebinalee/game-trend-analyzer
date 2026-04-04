from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.game import Game
from schemas.game import GameResponse

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("", response_model=list[GameResponse])
async def get_games(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game).where(Game.is_active == True))
    return result.scalars().all()
