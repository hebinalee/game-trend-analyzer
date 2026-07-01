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
    # --- Reddit 커뮤니티 (모바일 인기 Top 10) ---
    # app_id = subreddit 이름 (r/{app_id}), thumbnail_url은 프론트엔드 이니셜로 대체
    {"platform": "reddit", "name": "Genshin Impact",    "app_id": "Genshin_Impact",     "thumbnail_url": None},
    {"platform": "reddit", "name": "Clash of Clans",    "app_id": "ClashOfClans",        "thumbnail_url": None},
    {"platform": "reddit", "name": "Pokémon GO",        "app_id": "pokemongo",           "thumbnail_url": None},
    {"platform": "reddit", "name": "Brawl Stars",       "app_id": "Brawlstars",          "thumbnail_url": None},
    {"platform": "reddit", "name": "Clash Royale",      "app_id": "ClashRoyale",         "thumbnail_url": None},
    {"platform": "reddit", "name": "PUBG Mobile",       "app_id": "PUBGMobile",          "thumbnail_url": None},
    {"platform": "reddit", "name": "Mobile Legends",    "app_id": "MobileLegendsGame",   "thumbnail_url": None},
    {"platform": "reddit", "name": "Honkai: Star Rail", "app_id": "HonkaiStarRail",      "thumbnail_url": None},
    {"platform": "reddit", "name": "Wild Rift",         "app_id": "wildrift",            "thumbnail_url": None},
    {"platform": "reddit", "name": "Free Fire",         "app_id": "freefire",            "thumbnail_url": None},
]


async def init_db():
    from models.game import Game
    from models import alert  # noqa: F401 — Alert 테이블 생성을 위해 임포트
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # SEED_GAMES에 없는 게임은 비활성화 (플랫폼별 유효 app_id 집합으로 판단)
        seed_index: dict[str, set[str]] = {}
        for g in SEED_GAMES:
            seed_index.setdefault(g["platform"], set()).add(g["app_id"])

        all_games = (await session.execute(select(Game))).scalars().all()
        for game in all_games:
            if game.platform in seed_index and game.app_id not in seed_index[game.platform]:
                game.is_active = False

        # 신규 게임 추가
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
