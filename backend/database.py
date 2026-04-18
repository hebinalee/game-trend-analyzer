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


# Steam 인기 게임 Top 10 (Steam Charts 기준 동시접속자 상위권)
# thumbnail: https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg
SEED_GAMES = [
    {"name": "Counter-Strike 2", "app_id": "730", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg"},
    {"name": "Dota 2", "app_id": "570", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/570/header.jpg"},
    {"name": "PUBG: BATTLEGROUNDS", "app_id": "578080", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/578080/header.jpg"},
    {"name": "Elden Ring", "app_id": "1245620", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1245620/header.jpg"},
    {"name": "Baldur's Gate 3", "app_id": "1086940", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1086940/header.jpg"},
    {"name": "Rust", "app_id": "252490", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/252490/header.jpg"},
    {"name": "Cyberpunk 2077", "app_id": "1091500", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1091500/header.jpg"},
    {"name": "Valheim", "app_id": "892970", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/892970/header.jpg"},
    {"name": "Terraria", "app_id": "105600", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/105600/header.jpg"},
    {"name": "Team Fortress 2", "app_id": "440", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg"},
]


async def init_db():
    from models.game import Game
    from models import alert  # noqa: F401 — Alert 테이블 생성을 위해 임포트
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
