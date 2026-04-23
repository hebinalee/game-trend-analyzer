from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import async_session
from models.game import Game
from schemas.qa import QARequest, QAResponse
from analyzer.game_qa import answer_question

router = APIRouter(prefix="/api/qa", tags=["qa"])


async def get_db():
    async with async_session() as session:
        yield session


@router.post("", response_model=QAResponse)
async def ask(request: QARequest, db: AsyncSession = Depends(get_db)):
    """게임 운영 질문에 AI가 답변합니다. (Agent E — Game Ops QA)"""
    result = await db.execute(select(Game).where(Game.id == request.game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="게임을 찾을 수 없습니다.")

    response = await answer_question(game, request.question, db)
    return QAResponse(**response)
