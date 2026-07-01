"""
Reddit 커뮤니티 크롤러

Reddit OAuth2 API를 활용하여 게임별 서브레딧의 최근 게시글을 수집합니다.
- 신규 글: oauth.reddit.com/r/{subreddit}/new
- 공식 공지: 플레어(flair)가 patch/update/announcement인 게시글을 "news"로 분류

app_id (= subreddit 이름) 예시: "Genshin_Impact", "lostarkgame", "PUBGMobile"

사전 설정:
  1. https://www.reddit.com/prefs/apps 에서 "script" 타입 앱 등록
  2. .env에 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET 설정
  미설정 시 crawl_game()이 빈 리스트를 반환하고 경고 로그만 출력합니다.
"""
import logging
from datetime import datetime, timedelta

import httpx

from config import settings
from crawler.base_crawler import BaseCrawler
from crawler.utils import clean_text, random_delay
from models.game import Game

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_API_BASE = "https://oauth.reddit.com"
_USER_AGENT = "GameTrendAnalyzer/1.0 (by /u/gametrend_bot)"

# 이 플레어 키워드가 포함되면 post_type="news"로 분류
_NEWS_FLAIR_KEYWORDS = {"patch", "update", "announcement", "official", "notice", "dev", "hotfix"}


async def _fetch_token() -> str | None:
    """Reddit OAuth2 client_credentials 방식으로 액세스 토큰을 발급받는다."""
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                _TOKEN_URL,
                auth=(settings.reddit_client_id, settings.reddit_client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": _USER_AGENT},
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception as e:
            logger.error(f"Reddit 토큰 발급 실패: {e}")
            return None


async def _fetch_posts(subreddit: str, token: str, days_back: int = 1) -> list[dict]:
    """서브레딧의 최근 게시글을 수집한다."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    posts = []

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{_API_BASE}/r/{subreddit}/new",
                params={"limit": 100},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                item = child.get("data", {})
                created = datetime.utcfromtimestamp(item.get("created_utc", 0))
                if created < cutoff:
                    continue

                flair = (item.get("link_flair_text") or "").lower()
                post_type = "news" if any(k in flair for k in _NEWS_FLAIR_KEYWORDS) else "community"

                # 텍스트 게시글이면 selftext, 링크 게시글이면 url 사용
                content = item.get("selftext") or item.get("url", "")
                posts.append({
                    "post_id": f"reddit_{subreddit}_{item['id']}",
                    "source": "reddit",
                    "title": clean_text(item.get("title", ""), 500),
                    "content": clean_text(content),
                    "author": clean_text(item.get("author", "[deleted]"), 100),
                    "like_count": max(0, int(item.get("score", 0))),
                    "comment_count": int(item.get("num_comments", 0)),
                    "post_type": post_type,
                    "posted_at": created,
                })
        except Exception as e:
            logger.error(f"[reddit/r/{subreddit}] 게시글 수집 오류: {e}")

    return posts


class RedditCommunityCrawler(BaseCrawler):
    """Reddit 커뮤니티 크롤러."""

    platform = "mobile"

    def _games_query(self):
        from sqlalchemy import select
        return (
            select(Game)
            .where(Game.platform == "mobile", Game.is_active == True, Game.reddit_id.isnot(None))
        )

    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            logger.warning(
                "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 미설정 — Reddit 크롤링 건너뜀. "
                ".env.example 참고"
            )
            return []

        token = await _fetch_token()
        if not token:
            return []

        subreddit = game.reddit_id
        logger.info(f"[{game.name}] Reddit 수집 시작 (r/{subreddit})")
        posts = await _fetch_posts(subreddit, token, days_back)
        await random_delay(1, 2)
        logger.info(f"[{game.name}] 수집 완료: {len(posts)}건")
        return posts
