"""
Steam Community 크롤러

Steam Web API를 활용하여 게임별 최근 리뷰 및 뉴스를 수집합니다.
- 리뷰: store.steampowered.com/appreviews/{appid} (공식 API)
- 뉴스: api.steampowered.com/ISteamNews/GetNewsForApp/v2/ (공식 API)
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.game import Game
from models.post import Post
from crawler.utils import random_delay, clean_text
from storage.file_store import save_posts

logger = logging.getLogger(__name__)

STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews/{appid}"
STEAM_NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"


async def _fetch_reviews(app_id: str, days_back: int = 1) -> list[dict]:
    """Steam 리뷰 API에서 최근 리뷰를 수집한다."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    params = {
        "json": 1,
        "language": "all",
        "num_per_page": 100,
        "filter": "recent",
        "review_type": "all",
        "purchase_type": "all",
    }
    posts = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(STEAM_REVIEW_URL.format(appid=app_id), params=params)
            resp.raise_for_status()
            data = resp.json()
            for review in data.get("reviews", []):
                created = datetime.fromtimestamp(
                    review["timestamp_created"], tz=timezone.utc
                )
                if created < cutoff:
                    continue
                posts.append({
                    "post_id": f"{app_id}_review_{review['recommendationid']}",
                    "title": "Recommended" if review.get("voted_up") else "Not Recommended",
                    "content": clean_text(review.get("review", "")),
                    "author": review.get("author", {}).get("steamid", "unknown"),
                    "like_count": review.get("votes_up", 0),
                    "comment_count": review.get("comment_count", 0),
                    "post_type": "review",
                    "posted_at": created,
                })
        except Exception as e:
            logger.error(f"[app_id={app_id}] 리뷰 수집 오류: {e}")
    return posts


async def _fetch_news(app_id: str, days_back: int = 1) -> list[dict]:
    """Steam 뉴스 API에서 최근 공식 뉴스/패치노트를 수집한다."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    params = {
        "appid": app_id,
        "count": 20,
        "maxlength": 1000,
        "format": "json",
    }
    posts = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(STEAM_NEWS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("appnews", {}).get("newsitems", []):
                created = datetime.fromtimestamp(item["date"], tz=timezone.utc)
                if created < cutoff:
                    continue
                posts.append({
                    "post_id": f"{app_id}_news_{item['gid']}",
                    "title": clean_text(item.get("title", ""), 500),
                    "content": clean_text(item.get("contents", "")),
                    "author": clean_text(item.get("author", "Steam"), 100),
                    "like_count": 0,
                    "comment_count": 0,
                    "post_type": "news",
                    "posted_at": created,
                })
        except Exception as e:
            logger.error(f"[app_id={app_id}] 뉴스 수집 오류: {e}")
    return posts


async def crawl_game(game: Game, days_back: int = 1) -> list[dict]:
    """
    특정 Steam 게임의 최근 리뷰와 뉴스를 수집한다.
    반환: Post 생성에 필요한 dict 리스트
    """
    logger.info(f"[{game.name}] Steam 데이터 수집 시작 (app_id={game.app_id})")
    reviews = await _fetch_reviews(game.app_id, days_back)
    await random_delay(1, 2)
    news = await _fetch_news(game.app_id, days_back)
    posts = reviews + news
    logger.info(f"[{game.name}] 수집 완료: 리뷰 {len(reviews)}개, 뉴스 {len(news)}개")
    return posts


async def crawl_all_games(db_session: AsyncSession) -> None:
    """
    DB의 모든 active 게임에 대해 crawl_game을 순차 실행하고
    로컬 파일 및 DB에 저장한다.
    파일 저장은 DB 저장보다 먼저 수행되어 DB 장애 시에도 데이터를 보존한다.
    """
    from datetime import date as date_type
    result = await db_session.execute(select(Game).where(Game.is_active == True))
    games = result.scalars().all()
    today = date_type.today()

    for game in games:
        try:
            posts_data = await crawl_game(game, days_back=1)

            # 1. 파일 저장 (DB 저장 전에 수행 — 장애 안전망)
            if posts_data:
                crawled_at = datetime.now(timezone.utc)
                file_records = [
                    {**p, "crawled_at": crawled_at, "app_id": game.app_id}
                    for p in posts_data
                ]
                try:
                    save_posts(today, game.app_id, file_records)
                except Exception as fe:
                    logger.warning(f"[{game.name}] 파일 저장 실패 (DB 저장 계속): {fe}")

            # 2. DB 저장
            for post_dict in posts_data:
                existing = await db_session.execute(
                    select(Post).where(Post.post_id == post_dict["post_id"])
                )
                if existing.scalar_one_or_none():
                    continue
                db_session.add(Post(
                    game_id=game.id,
                    crawled_at=datetime.now(timezone.utc),
                    **post_dict,
                ))

            await db_session.commit()
            logger.info(f"[{game.name}] DB 저장 완료")

        except Exception as e:
            await db_session.rollback()
            logger.error(f"[{game.name}] DB 저장 오류: {e}")

        await random_delay(1, 3)
