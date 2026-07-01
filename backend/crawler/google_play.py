"""
Google Play Store 리뷰 크롤러

google-play-scraper 라이브러리를 사용하여 Android 앱 리뷰를 수집합니다.
- 인증 불필요 (비공식 API)
- rating(1~5), thumbsUpCount(like_count) 수집 가능

app_id(= play_store_id) 예시: "com.miHoYo.GenshinImpact"
"""
import logging
from datetime import datetime, timedelta

from crawler.base_crawler import BaseCrawler
from crawler.utils import clean_text
from models.game import Game

logger = logging.getLogger(__name__)

_SORT_NEWEST = 2  # google_play_scraper Sort.NEWEST


def _fetch_reviews_sync(package: str, days_back: int) -> list[dict]:
    """동기 함수 — 스레드풀에서 실행됩니다."""
    try:
        from google_play_scraper import reviews, Sort
    except ImportError:
        logger.error("google-play-scraper 미설치 — pip install google-play-scraper")
        return []

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    result = []
    continuation_token = None

    while True:
        batch, continuation_token = reviews(
            package,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=200,
            continuation_token=continuation_token,
        )
        if not batch:
            break

        for r in batch:
            at: datetime = r.get("at") or datetime.utcnow()
            if at < cutoff:
                return result  # 오래된 리뷰 도달 시 중단

            result.append({
                "post_id": f"gplay_{package}_{r['reviewId']}",
                "source": "google_play",
                "title": None,
                "content": clean_text(r.get("content") or "", 1000),
                "author": clean_text(r.get("userName") or "", 100),
                "rating": float(r.get("score", 0)),
                "like_count": int(r.get("thumbsUpCount", 0)),
                "comment_count": None,
                "post_type": "review",
                "posted_at": at,
            })

        if not continuation_token:
            break

    return result


class GooglePlayCrawler(BaseCrawler):
    """Google Play Store 리뷰 크롤러."""

    platform = "mobile"

    def _games_query(self):
        from sqlalchemy import select
        return (
            select(Game)
            .where(Game.platform == "mobile", Game.is_active == True, Game.play_store_id.isnot(None))
        )

    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        import asyncio
        package = game.play_store_id
        logger.info(f"[{game.name}] Google Play 수집 시작 (패키지={package})")
        try:
            loop = asyncio.get_event_loop()
            posts = await loop.run_in_executor(None, _fetch_reviews_sync, package, days_back)
        except Exception as e:
            logger.error(f"[{game.name}] Google Play 수집 오류: {e}")
            return []
        logger.info(f"[{game.name}] Google Play 수집 완료: {len(posts)}건")
        return posts
