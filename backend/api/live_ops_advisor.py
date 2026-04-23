from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import async_session
from models.game import Game
from schemas.live_ops_advisor import LiveOpsAdvisorRequest, LiveOpsAdvisorResponse
from analyzer.live_ops_advisor import answer_question

router = APIRouter(prefix="/api/live-ops-advisor", tags=["live-ops-advisor"])


async def get_db():
    async with async_session() as session:
        yield session


@router.post("", response_model=LiveOpsAdvisorResponse)
async def ask(request: LiveOpsAdvisorRequest, db: AsyncSession = Depends(get_db)):
    """게임 운영 질문에 AI가 답변합니다. (Agent E — Game LiveOps Advisor)"""
    result = await db.execute(select(Game).where(Game.id == request.game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="게임을 찾을 수 없습니다.")

    response = await answer_question(game, request.question, db)
    return LiveOpsAdvisorResponse(**response)
