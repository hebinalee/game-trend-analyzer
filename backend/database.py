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
    # --- Steam PC 게임 ---
    {"platform": "steam", "name": "Counter-Strike 2", "app_id": "730", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg"},
    {"platform": "steam", "name": "Dota 2", "app_id": "570", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/570/header.jpg"},
    {"platform": "steam", "name": "PUBG: BATTLEGROUNDS", "app_id": "578080", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/578080/header.jpg"},
    {"platform": "steam", "name": "Elden Ring", "app_id": "1245620", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1245620/header.jpg"},
    {"platform": "steam", "name": "Baldur's Gate 3", "app_id": "1086940", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1086940/header.jpg"},
    {"platform": "steam", "name": "Rust", "app_id": "252490", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/252490/header.jpg"},
    {"platform": "steam", "name": "Cyberpunk 2077", "app_id": "1091500", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1091500/header.jpg"},
    {"platform": "steam", "name": "Valheim", "app_id": "892970", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/892970/header.jpg"},
    {"platform": "steam", "name": "Terraria", "app_id": "105600", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/105600/header.jpg"},
    {"platform": "steam", "name": "Team Fortress 2", "app_id": "440", "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg"},
    # --- 네이버 게임 라운지 (모바일/온라인 게임) ---
    # app_id = 네이버 게임 라운지 lounge_id
    {"platform": "naver", "name": "리니지M", "app_id": "lineagem", "thumbnail_url": "https://game.naver.com/static/game_detail/lineagem/hero_image.jpg"},
    {"platform": "naver", "name": "메이플스토리M", "app_id": "maplestorym", "thumbnail_url": "https://game.naver.com/static/game_detail/maplestorym/hero_image.jpg"},
    {"platform": "naver", "name": "배틀그라운드 모바일", "app_id": "pubgmobile", "thumbnail_url": "https://game.naver.com/static/game_detail/pubgmobile/hero_image.jpg"},
    {"platform": "naver", "name": "원신", "app_id": "genshin", "thumbnail_url": "https://game.naver.com/static/game_detail/genshin/hero_image.jpg"},
    {"platform": "naver", "name": "로스트아크", "app_id": "lostark", "thumbnail_url": "https://game.naver.com/static/game_detail/lostark/hero_image.jpg"},
]


async def init_db():
    from models.game import Game
    from models import alert  # noqa: F401 — Alert 테이블 생성을 위해 임포트
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for game_data in SEED_GAMES:
            existing = await session.execute(
                select(Game).where(
                    Game.platform == game_data["platform"],
                    Game.app_id == game_data["app_id"],
                )
            )
            if not existing.scalar_one_or_none():
                session.add(Game(**game_data))
        await session.commit()
