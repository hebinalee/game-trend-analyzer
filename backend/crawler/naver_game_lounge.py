"""
네이버 게임 라운지 크롤러

네이버 게임 라운지(game.naver.com/lounge)의 커뮤니티 게시글을 수집합니다.
- 커뮤니티 게시글: game.naver.com/lounge/{lounge_id}/community (자유게시판, 공략 등)
- 공지/패치노트: game.naver.com/lounge/{lounge_id}/notice

app_id (= lounge_id) 예시: "lineagem", "maplestorym", "pubgmobile", "genshin", "lostark"
"""
import logging
from datetime import datetime, timedelta

import httpx

from crawler.base_crawler import BaseCrawler
from crawler.utils import clean_text, random_delay
from models.game import Game

logger = logging.getLogger(__name__)

# 네이버 게임 라운지 내부 API 엔드포인트
_COMMUNITY_API = (
    "https://game.naver.com/api/v2/community/lounge/{lounge_id}"
    "/community/board/post/list"
)
_NOTICE_API = (
    "https://game.naver.com/api/v2/community/lounge/{lounge_id}"
    "/notice/post/list"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://game.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


async def _fetch_community_posts(lounge_id: str, days_back: int = 1) -> list[dict]:
    """자유게시판/커뮤니티 게시글 수집."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    posts = []

    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        try:
            resp = await client.get(
                _COMMUNITY_API.format(lounge_id=lounge_id),
                params={"page": 1, "pageSize": 30, "orderType": "NEW"},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("result", {}).get("postList", []):
                created = _parse_naver_date(item.get("regDate") or item.get("createDate", ""))
                if created and created < cutoff:
                    continue
                posts.append({
                    "post_id": f"naver_{lounge_id}_post_{item['postId']}",
                    "source": "naver",
                    "title": clean_text(item.get("subject", ""), 500),
                    "content": clean_text(item.get("contentSummary") or item.get("content", "")),
                    "author": clean_text(item.get("nickName") or item.get("writerNickName", ""), 100),
                    "like_count": int(item.get("likeItCount") or item.get("recommendCount", 0)),
                    "comment_count": int(item.get("commentCount", 0)),
                    "post_type": "community",
                    "posted_at": created,
                })
        except Exception as e:
            logger.error(f"[naver/{lounge_id}] 커뮤니티 수집 오류: {e}")

    return posts


async def _fetch_notice_posts(lounge_id: str, days_back: int = 1) -> list[dict]:
    """공지/패치노트 수집."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    posts = []

    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        try:
            resp = await client.get(
                _NOTICE_API.format(lounge_id=lounge_id),
                params={"page": 1, "pageSize": 20},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("result", {}).get("postList", []):
                created = _parse_naver_date(item.get("regDate") or item.get("createDate", ""))
                if created and created < cutoff:
                    continue
                posts.append({
                    "post_id": f"naver_{lounge_id}_notice_{item['postId']}",
                    "source": "naver",
                    "title": clean_text(item.get("subject", ""), 500),
                    "content": clean_text(item.get("contentSummary") or item.get("content", "")),
                    "author": clean_text(item.get("nickName") or item.get("writerNickName", "official"), 100),
                    "like_count": 0,
                    "comment_count": int(item.get("commentCount", 0)),
                    "post_type": "news",
                    "posted_at": created,
                })
        except Exception as e:
            logger.error(f"[naver/{lounge_id}] 공지 수집 오류: {e}")

    return posts


def _parse_naver_date(date_str: str) -> datetime | None:
    """네이버 날짜 문자열을 datetime으로 변환."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return datetime.strptime(date_str[:19], fmt)
        except ValueError:
            continue
    return None


class NaverGameLoungeCrawler(BaseCrawler):
    """네이버 게임 라운지 크롤러."""

    platform = "naver"

    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        lounge_id = game.app_id
        logger.info(f"[{game.name}] 네이버 라운지 수집 시작 (lounge_id={lounge_id})")

        community = await _fetch_community_posts(lounge_id, days_back)
        await random_delay(1, 2)
        notices = await _fetch_notice_posts(lounge_id, days_back)

        posts = community + notices
        logger.info(
            f"[{game.name}] 수집 완료: 커뮤니티 {len(community)}개, 공지 {len(notices)}개"
        )
        return posts
