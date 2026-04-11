"""
Claude API 기반 게임 커뮤니티 동향 분석 엔진
"""
import json
import logging
from datetime import date, datetime, timedelta

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from models.game import Game
from models.post import Post
from models.report import Report

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "당신은 게임 운영 전문 애널리스트입니다. "
    "Steam 커뮤니티의 유저 리뷰와 공식 뉴스를 분석하여 "
    "운영자/기획자/마케터가 즉시 활용할 수 있는 인사이트를 한국어로 제공합니다."
)

USER_PROMPT_TEMPLATE = """다음은 Steam '{game_name}' 게임의 최근 데이터 {count}건입니다.
(리뷰: 유저 작성, 뉴스: 공식 패치노트/공지)

{posts_text}

위 데이터를 분석하여 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요.
리뷰의 "Recommended"/"Not Recommended" 여부를 sentiment 산정에 반영하세요.

{{
  "summary": "전체 동향 3~5줄 요약",
  "hot_topics": ["화제1", "화제2", "..."],
  "sentiment": {{"positive": 0.0, "negative": 0.0, "neutral": 0.0}},
  "key_issues": {{
    "bugs": ["버그1", "..."],
    "requests": ["요청사항1", "..."],
    "operations": ["운영이슈1", "..."]
  }},
  "trend_keywords": ["키워드1", "키워드2", "..."]
}}"""


def _build_posts_text(posts: list[Post]) -> str:
    lines = []
    for i, post in enumerate(posts, 1):
        label = f"[{post.post_type.upper()}]" if post.post_type else ""
        lines.append(f"[{i}] {label} {post.title or '(제목 없음)'}")
        if post.content:
            lines.append(f"    {post.content[:300]}")
        lines.append(f"    좋아요: {post.like_count} | 댓글: {post.comment_count}")
        lines.append("")
    return "\n".join(lines)


async def analyze_game_posts(game: Game, posts: list[Post]) -> dict:
    """
    게시글 목록을 LLM으로 분석하고 리포트 dict를 반환한다.
    """
    # 50개 초과 시 인기순 상위 50개만 사용
    if len(posts) > 50:
        posts = sorted(posts, key=lambda p: p.like_count + p.comment_count, reverse=True)[:50]

    posts_text = _build_posts_text(posts)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        game_name=game.name,
        count=len(posts),
        posts_text=posts_text,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text.strip()
    # JSON 블록만 추출
    if "```" in response_text:
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    result = json.loads(response_text)
    return result


async def analyze_all_games(db_session: AsyncSession) -> None:
    """
    모든 active 게임에 대해 오늘 날짜 리포트를 생성하고 DB에 저장한다 (upsert).
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    games_result = await db_session.execute(select(Game).where(Game.is_active == True))
    games = games_result.scalars().all()

    for game in games:
        try:
            # 전날 수집된 게시글 조회
            cutoff_start = datetime.combine(yesterday, datetime.min.time())
            cutoff_end = datetime.combine(today, datetime.min.time())

            posts_result = await db_session.execute(
                select(Post)
                .where(Post.game_id == game.id)
                .where(Post.crawled_at >= cutoff_start)
                .where(Post.crawled_at < cutoff_end)
            )
            posts = posts_result.scalars().all()

            if not posts:
                logger.info(f"[{game.name}] 분석할 게시글 없음, 건너뜀.")
                continue

            logger.info(f"[{game.name}] {len(posts)}개 게시글 분석 시작")
            analysis = await analyze_game_posts(game, posts)

            # Upsert
            stmt = pg_insert(Report).values(
                game_id=game.id,
                report_date=today,
                summary=analysis.get("summary"),
                hot_topics=analysis.get("hot_topics"),
                sentiment=analysis.get("sentiment"),
                key_issues=analysis.get("key_issues"),
                trend_keywords=analysis.get("trend_keywords"),
                raw_post_count=len(posts),
                created_at=datetime.utcnow(),
            ).on_conflict_do_update(
                constraint="uq_game_report_date",
                set_={
                    "summary": analysis.get("summary"),
                    "hot_topics": analysis.get("hot_topics"),
                    "sentiment": analysis.get("sentiment"),
                    "key_issues": analysis.get("key_issues"),
                    "trend_keywords": analysis.get("trend_keywords"),
                    "raw_post_count": len(posts),
                    "created_at": datetime.utcnow(),
                },
            )
            await db_session.execute(stmt)
            await db_session.commit()
            logger.info(f"[{game.name}] 리포트 저장 완료")

        except Exception as e:
            await db_session.rollback()
            logger.error(f"[{game.name}] 분석 오류: {e}")
            continue
