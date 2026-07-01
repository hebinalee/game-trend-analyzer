"""
Apple App Store 리뷰 크롤러

iTunes Customer Reviews RSS를 사용하여 iOS 앱 리뷰를 수집합니다.
- 인증 불필요 (공식 RSS 엔드포인트)
- rating(1~5) 수집 가능, like_count 미제공(null)
- 최대 ~500개 리뷰 (페이지당 50개 × 최대 10페이지)

RSS URL: https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from crawler.base_crawler import BaseCrawler
from crawler.utils import clean_text, random_delay
from models.game import Game

logger = logging.getLogger(__name__)

_RSS_URL = "https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
_MAX_PAGES = 10


async def _fetch_reviews(app_id: str, days_back: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    posts = []

    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, _MAX_PAGES + 1):
            try:
                resp = await client.get(_RSS_URL.format(page=page, app_id=app_id))
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"[AppStore] 페이지 {page} 수집 오류: {e}")
                break

            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break

            # 첫 번째 entry는 앱 정보 메타데이터이므로 건너뜀
            for entry in entries[1:] if page == 1 else entries:
                try:
                    updated_str = entry.get("updated", {}).get("label", "")
                    updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(timezone.utc)

                    if updated < cutoff:
                        return posts  # 오래된 리뷰 도달 시 중단

                    review_id = entry.get("id", {}).get("label", f"unknown_{page}")
                    rating_str = entry.get("im:rating", {}).get("label", "0")
                    title = entry.get("title", {}).get("label", "")
                    content = entry.get("content", {}).get("label", "")
                    author = entry.get("author", {}).get("name", {}).get("label", "")

                    posts.append({
                        "post_id": f"appstore_{app_id}_{review_id}",
                        "source": "app_store",
                        "title": clean_text(title, 500),
                        "content": clean_text(content, 1000),
                        "author": clean_text(author, 100),
                        "rating": float(rating_str) if rating_str.isdigit() else None,
                        "like_count": None,   # App Store RSS에서 미제공
                        "comment_count": None,
                        "post_type": "review",
                        "posted_at": updated.replace(tzinfo=None),
                    })
                except Exception as e:
                    logger.warning(f"[AppStore] 리뷰 파싱 오류: {e}")
                    continue

            await random_delay(0.5, 1)

    return posts


class AppStoreCrawler(BaseCrawler):
    """Apple App Store 리뷰 크롤러."""

    platform = "mobile"

    def _games_query(self):
        from sqlalchemy import select
        return (
            select(Game)
            .where(Game.platform == "mobile", Game.is_active == True, Game.app_store_id.isnot(None))
        )

    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        app_id = game.app_store_id
        logger.info(f"[{game.name}] App Store 수집 시작 (app_id={app_id})")
        try:
            posts = await _fetch_reviews(app_id, days_back)
        except Exception as e:
            logger.error(f"[{game.name}] App Store 수집 오류: {e}")
            return []
        logger.info(f"[{game.name}] App Store 수집 완료: {len(posts)}건")
        return posts
