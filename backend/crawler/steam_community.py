"""
Steam Community 크롤러

Steam Web API를 활용하여 게임별 최근 리뷰 및 뉴스를 수집합니다.
- 리뷰: store.steampowered.com/appreviews/{appid} (공식 API)
- 뉴스: api.steampowered.com/ISteamNews/GetNewsForApp/v2/ (공식 API)
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from crawler.base_crawler import BaseCrawler
from crawler.utils import random_delay, clean_text
from models.game import Game

logger = logging.getLogger(__name__)

STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews/{appid}"
STEAM_NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"


async def _fetch_reviews(app_id: str, days_back: int = 1) -> list[dict]:
    """Steam 리뷰 API에서 최근 리뷰를 수집한다."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
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
                ).replace(tzinfo=None)
                if created < cutoff:
                    continue
                posts.append({
                    "post_id": f"{app_id}_review_{review['recommendationid']}",
                    "source": "steam",
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
    cutoff = datetime.utcnow() - timedelta(days=days_back)
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
                created = datetime.fromtimestamp(item["date"], tz=timezone.utc).replace(tzinfo=None)
                if created < cutoff:
                    continue
                posts.append({
                    "post_id": f"{app_id}_news_{item['gid']}",
                    "source": "steam",
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


class SteamCommunityCrawler(BaseCrawler):
    """Steam 커뮤니티 크롤러."""

    platform = "steam"

    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        logger.info(f"[{game.name}] Steam 데이터 수집 시작 (app_id={game.app_id})")
        reviews = await _fetch_reviews(game.app_id, days_back)
        await random_delay(1, 2)
        news = await _fetch_news(game.app_id, days_back)
        posts = reviews + news
        logger.info(f"[{game.name}] 수집 완료: 리뷰 {len(reviews)}개, 뉴스 {len(news)}개")
        return posts


# 하위 호환: scheduler 등에서 직접 호출하던 모듈 함수 유지
_steam_crawler = SteamCommunityCrawler()
crawl_game = _steam_crawler.crawl_game
crawl_all_games = _steam_crawler.crawl_all_games
