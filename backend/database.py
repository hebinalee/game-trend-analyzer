from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings


engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SEED_GAMES = [
    {"name": "리그 오브 레전드", "lounge_id": "lol", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/lol_logo.png"},
    {"name": "메이플스토리", "lounge_id": "maplestory", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/maplestory_logo.png"},
    {"name": "피파 온라인 4", "lounge_id": "fifaonline4", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/fifaonline4_logo.png"},
    {"name": "오버워치 2", "lounge_id": "overwatch2", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/overwatch2_logo.png"},
    {"name": "배틀그라운드", "lounge_id": "pubg", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/pubg_logo.png"},
    {"name": "로스트아크", "lounge_id": "lostark", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/lostark_logo.png"},
    {"name": "발로란트", "lounge_id": "valorant", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/valorant_logo.png"},
    {"name": "던전앤파이터", "lounge_id": "df", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/df_logo.png"},
    {"name": "스타크래프트", "lounge_id": "starcraft", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/starcraft_logo.png"},
    {"name": "서든어택", "lounge_id": "suddenattack", "thumbnail_url": "https://game.naver.com/static_web/images/game_lounge/suddenattack_logo.png"},
]


async def init_db():
    from models.game import Game
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(Game))
        existing = result.scalars().all()
        if not existing:
            for game_data in SEED_GAMES:
                game = Game(**game_data)
                session.add(game)
            await session.commit()
