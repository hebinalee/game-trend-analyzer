"""
Agent E — Game LiveOps Advisor
==============================
Claude Tool Use 기반 게임 운영 질문 답변 엔진.

RAG 대신 Tool Use를 사용하는 이유:
  - 구조화된 DB 데이터에는 정확한 SQL 쿼리가 근사 벡터 검색보다 우수
  - 날짜 필터링·감성 집계는 Tool Use로 정확하게 처리 가능
  - 추가 인프라(벡터 DB) 불필요
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models.game import Game
from models.post import Post

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 게임 운영 전문 AI 어시스턴트입니다.
Steam 유저 리뷰와 공식 패치노트 데이터를 분석하여 게임 운영자/기획자/마케터의 질문에 답변합니다.

답변 원칙:
1. 데이터에 기반한 근거 있는 분석을 제공한다
2. 구체적인 수치(비율, 건수, 날짜)를 활용한다
3. 운영자가 즉시 실행할 수 있는 액션 아이템을 제안한다
4. 데이터가 부족하면 솔직하게 한계를 언급한다
5. 한국어로 답변한다"""

TOOLS = [
    {
        "name": "get_recent_reviews",
        "description": (
            "최근 N일간의 유저 리뷰를 가져온다. 감성 비율(긍정/부정)과 리뷰 샘플을 반환한다. "
            "리텐션 이슈, 전반적인 유저 반응 파악에 사용한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {"type": "integer", "description": "최근 몇 일간의 리뷰 (기본 7)"},
                "sentiment": {"type": "string", "enum": ["all", "positive", "negative"],
                              "description": "감성 필터 (기본 all)"},
                "limit": {"type": "integer", "description": "반환할 최대 리뷰 수 (기본 50)"},
            },
            "required": ["days_back"],
        },
    },
    {
        "name": "get_patch_notes",
        "description": (
            "최근 N일간의 공식 패치노트와 공지를 가져온다. "
            "패치 전후 비교, 특정 업데이트의 영향 분석에 사용한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {"type": "integer", "description": "최근 몇 일간의 패치노트 (기본 30)"},
            },
            "required": ["days_back"],
        },
    },
    {
        "name": "get_sentiment_stats",
        "description": (
            "기간별 감성 트렌드를 일별로 분석한다. "
            "리텐션 변화 추적, 시간대별 반응 패턴 파악에 사용한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {"type": "integer", "description": "분석할 기간 일수 (기본 7)"},
            },
            "required": ["days_back"],
        },
    },
    {
        "name": "search_by_keyword",
        "description": (
            "특정 키워드가 포함된 리뷰를 검색한다. "
            "특정 기능·아이템·이벤트에 대한 유저 반응 파악에 사용한다. "
            "예: 코스튬, 밸런스, 서버 등."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "검색할 키워드 목록 (한국어·영어 모두 가능)",
                },
                "days_back": {"type": "integer", "description": "최근 몇 일간 검색 (기본 14)"},
            },
            "required": ["keywords"],
        },
    },
]


# ── DB 기반 Tool 구현 ─────────────────────────────────────────────────────────

async def _get_recent_reviews(db: AsyncSession, game_id: int,
                               days_back: int = 7, sentiment: str = "all",
                               limit: int = 50) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    result = await db.execute(
        select(Post)
        .where(Post.game_id == game_id)
        .where(Post.post_type == "review")
        .where(Post.crawled_at >= cutoff)
    )
    posts = result.scalars().all()

    if sentiment == "positive":
        posts = [p for p in posts if p.title == "Recommended"]
    elif sentiment == "negative":
        posts = [p for p in posts if p.title == "Not Recommended"]

    total = len(posts)
    neg = sum(1 for p in posts if p.title == "Not Recommended")
    sampled = sorted(posts, key=lambda p: p.like_count, reverse=True)[:limit]

    return {
        "total_reviews": total,
        "negative_ratio": round(neg / total, 3) if total else 0,
        "positive_ratio": round((total - neg) / total, 3) if total else 0,
        "reviews": [
            {"recommended": p.title == "Recommended",
             "content": p.content or "",
             "votes_up": p.like_count,
             "posted_at": p.posted_at.isoformat() if p.posted_at else ""}
            for p in sampled
        ],
    }


async def _get_patch_notes(db: AsyncSession, game_id: int, days_back: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    result = await db.execute(
        select(Post)
        .where(Post.game_id == game_id)
        .where(Post.post_type == "news")
        .where(Post.crawled_at >= cutoff)
        .order_by(Post.posted_at.desc())
    )
    posts = result.scalars().all()

    patch_kws = ["patch", "update", "hotfix", "fix", "balance"]
    patches = [p for p in posts if any(kw in (p.title or "").lower() for kw in patch_kws)]
    announcements = [p for p in posts if p not in patches]

    return {
        "total_news": len(posts),
        "patch_count": len(patches),
        "patches": [{"title": p.title,
                     "content": (p.content or "")[:400],
                     "posted_at": p.posted_at.isoformat() if p.posted_at else ""}
                    for p in patches],
        "announcements": [{"title": p.title,
                           "posted_at": p.posted_at.isoformat() if p.posted_at else ""}
                          for p in announcements],
    }


async def _get_sentiment_stats(db: AsyncSession, game_id: int, days_back: int = 7) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    result = await db.execute(
        select(Post)
        .where(Post.game_id == game_id)
        .where(Post.post_type == "review")
        .where(Post.crawled_at >= cutoff)
    )
    posts = result.scalars().all()

    daily: dict[str, dict] = {}
    for p in posts:
        day = (p.posted_at or p.crawled_at).strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"total": 0, "positive": 0, "negative": 0}
        daily[day]["total"] += 1
        if p.title == "Recommended":
            daily[day]["positive"] += 1
        else:
            daily[day]["negative"] += 1

    for data in daily.values():
        data["negative_ratio"] = round(data["negative"] / data["total"], 3) if data["total"] else 0

    total = len(posts)
    neg = sum(1 for p in posts if p.title == "Not Recommended")

    return {
        "period_days": days_back,
        "total_reviews": total,
        "overall_negative_ratio": round(neg / total, 3) if total else 0,
        "overall_positive_ratio": round((total - neg) / total, 3) if total else 0,
        "daily_breakdown": dict(sorted(daily.items())),
    }


async def _search_by_keyword(db: AsyncSession, game_id: int,
                              keywords: list[str], days_back: int = 14) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    result = await db.execute(
        select(Post)
        .where(Post.game_id == game_id)
        .where(Post.post_type == "review")
        .where(Post.crawled_at >= cutoff)
    )
    posts = result.scalars().all()

    matched = []
    for p in posts:
        text = ((p.title or "") + " " + (p.content or "")).lower()
        hits = [kw for kw in keywords if kw.lower() in text]
        if hits:
            matched.append({
                "recommended": p.title == "Recommended",
                "content": p.content or "",
                "matched_keywords": hits,
                "votes_up": p.like_count,
                "posted_at": p.posted_at.isoformat() if p.posted_at else "",
            })

    matched.sort(key=lambda r: r["votes_up"], reverse=True)
    neg = sum(1 for r in matched if not r["recommended"])

    return {
        "keyword_match_count": len(matched),
        "match_ratio": round(len(matched) / len(posts), 3) if posts else 0,
        "negative_ratio_in_matches": round(neg / len(matched), 3) if matched else 0,
        "top_matches": matched[:10],
    }


# ── QA Agent Loop ─────────────────────────────────────────────────────────────

async def answer_question(game: Game, question: str, db: AsyncSession) -> dict:
    """
    게임 운영 질문에 Tool Use로 답변한다.
    반환: {answer, tools_used, game_name}
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    messages = [{"role": "user",
                 "content": f"게임: {game.name}\n\n질문: {question}"}]
    tools_used: list[str] = []

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    inp = block.input

                    if block.name == "get_recent_reviews":
                        result = await _get_recent_reviews(
                            db, game.id,
                            inp.get("days_back", 7),
                            inp.get("sentiment", "all"),
                            inp.get("limit", 50),
                        )
                    elif block.name == "get_patch_notes":
                        result = await _get_patch_notes(db, game.id, inp.get("days_back", 30))
                    elif block.name == "get_sentiment_stats":
                        result = await _get_sentiment_stats(db, game.id, inp.get("days_back", 7))
                    elif block.name == "search_by_keyword":
                        result = await _search_by_keyword(
                            db, game.id,
                            inp.get("keywords", []),
                            inp.get("days_back", 14),
                        )
                    else:
                        result = {"error": f"unknown tool: {block.name}"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            answer = "".join(b.text for b in response.content if hasattr(b, "text"))
            logger.info(f"[QA] {game.name} | tools={tools_used} | q={question[:50]}")
            return {
                "answer": answer.strip(),
                "tools_used": list(dict.fromkeys(tools_used)),  # 순서 유지 중복 제거
                "game_name": game.name,
            }
