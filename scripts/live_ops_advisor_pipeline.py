"""
Game LiveOps Advisor — Agent E POC
===================================
수집된 리뷰·패치 데이터를 바탕으로 게임 운영자의 질문에 답변하는 서비스 데모.

RAG 대신 Claude Tool Use를 사용하는 이유:
  - 데이터가 구조화되어 있어 SQL 기반 정확 쿼리가 가능
  - 날짜 필터링·집계(비율·건수)는 근사값이 아닌 정확한 값이 필요
  - 벡터 DB 등 추가 인프라 불필요

실행:
  python scripts/live_ops_advisor_pipeline.py --game "Elden Ring"               # 데모 모드 (예시 질문 3개 자동)
  python scripts/live_ops_advisor_pipeline.py --game "Elden Ring" --interactive  # 대화형 모드
  python scripts/live_ops_advisor_pipeline.py --game "Elden Ring" --days 14     # 수집 기간 조정 (기본 7일)
  python scripts/live_ops_advisor_pipeline.py --game "Elden Ring" --save        # 결과를 reports/ 에 마크다운으로 저장
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 데이터 수집 ────────────────────────────────────────────────────────────────

def clean(text: str, limit: int = 500) -> str:
    import re
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


async def search_steam_game(query: str) -> dict | None:
    """Steam Store Search API로 게임 검색 후 1위 반환."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": query, "l": "english", "cc": "US"},
        )
        items = resp.json().get("items", [])
    if not items:
        return None
    return {"name": items[0]["name"], "app_id": str(items[0]["id"])}


async def fetch_game_data(app_id: str, game_name: str, days_back: int = 7) -> dict:
    """Steam API에서 리뷰와 뉴스를 수집한다."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    reviews = []
    news = []

    async with httpx.AsyncClient(timeout=30) as client:
        # 리뷰
        try:
            resp = await client.get(
                f"https://store.steampowered.com/appreviews/{app_id}",
                params={"json": 1, "language": "all", "num_per_page": 100,
                        "filter": "recent", "review_type": "all", "purchase_type": "all"},
            )
            resp.raise_for_status()
            for r in resp.json().get("reviews", []):
                created = datetime.fromtimestamp(r["timestamp_created"], tz=timezone.utc)
                if created < cutoff:
                    continue
                reviews.append({
                    "recommended": r.get("voted_up", False),
                    "content": clean(r.get("review", "")),
                    "votes_up": r.get("votes_up", 0),
                    "posted_at": created.isoformat(),
                })
        except Exception as e:
            print(f"  리뷰 수집 오류: {e}")

        await asyncio.sleep(2)

        # 뉴스
        try:
            resp = await client.get(
                "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
                params={"appid": app_id, "count": 20, "maxlength": 800, "format": "json"},
            )
            resp.raise_for_status()
            for item in resp.json().get("appnews", {}).get("newsitems", []):
                created = datetime.fromtimestamp(item["date"], tz=timezone.utc)
                if created < cutoff:
                    continue
                title = clean(item.get("title", ""), 200)
                news.append({
                    "title": title,
                    "content": clean(item.get("contents", "")),
                    "posted_at": created.isoformat(),
                    "is_patch": any(kw in title.lower()
                                    for kw in ["patch", "update", "hotfix", "fix", "balance"]),
                })
        except Exception as e:
            print(f"  뉴스 수집 오류: {e}")

    return {"game_name": game_name, "app_id": app_id,
            "reviews": reviews, "news": news, "days_back": days_back}


# ── Tool 구현 ─────────────────────────────────────────────────────────────────

def tool_get_recent_reviews(game_data: dict, days_back: int = 7,
                             sentiment: str = "all", limit: int = 30) -> dict:
    reviews = game_data["reviews"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = [r for r in reviews
                if datetime.fromisoformat(r["posted_at"]) >= cutoff]

    if sentiment == "positive":
        filtered = [r for r in filtered if r["recommended"]]
    elif sentiment == "negative":
        filtered = [r for r in filtered if not r["recommended"]]

    filtered.sort(key=lambda r: r["votes_up"], reverse=True)
    sampled = filtered[:limit]

    total = len(filtered)
    neg = sum(1 for r in filtered if not r["recommended"])

    return {
        "total_reviews": total,
        "negative_ratio": round(neg / total, 3) if total else 0,
        "positive_ratio": round((total - neg) / total, 3) if total else 0,
        "reviews": [{"recommended": r["recommended"], "content": r["content"],
                     "votes_up": r["votes_up"], "posted_at": r["posted_at"]}
                    for r in sampled],
    }


def tool_get_patch_notes(game_data: dict, days_back: int = 30) -> dict:
    news = game_data["news"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = [n for n in news
                if datetime.fromisoformat(n["posted_at"]) >= cutoff]
    filtered.sort(key=lambda n: n["posted_at"], reverse=True)

    patches = [n for n in filtered if n["is_patch"]]
    announcements = [n for n in filtered if not n["is_patch"]]

    return {
        "total_news": len(filtered),
        "patch_count": len(patches),
        "patches": [{"title": n["title"], "content": n["content"][:400],
                     "posted_at": n["posted_at"]} for n in patches],
        "announcements": [{"title": n["title"], "posted_at": n["posted_at"]}
                          for n in announcements],
    }


def tool_get_sentiment_stats(game_data: dict, days_back: int = 7) -> dict:
    reviews = game_data["reviews"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = [r for r in reviews
                if datetime.fromisoformat(r["posted_at"]) >= cutoff]

    daily: dict[str, dict] = {}
    for r in filtered:
        day = r["posted_at"][:10]
        if day not in daily:
            daily[day] = {"total": 0, "positive": 0, "negative": 0}
        daily[day]["total"] += 1
        if r["recommended"]:
            daily[day]["positive"] += 1
        else:
            daily[day]["negative"] += 1

    for data in daily.values():
        data["negative_ratio"] = round(data["negative"] / data["total"], 3) if data["total"] else 0

    total = len(filtered)
    neg = sum(1 for r in filtered if not r["recommended"])

    return {
        "period_days": days_back,
        "total_reviews": total,
        "overall_negative_ratio": round(neg / total, 3) if total else 0,
        "overall_positive_ratio": round((total - neg) / total, 3) if total else 0,
        "daily_breakdown": dict(sorted(daily.items())),
    }


def tool_search_by_keyword(game_data: dict, keywords: list[str],
                            days_back: int = 14) -> dict:
    reviews = game_data["reviews"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    filtered = [r for r in reviews
                if datetime.fromisoformat(r["posted_at"]) >= cutoff]

    matched = []
    for r in filtered:
        text = r["content"].lower()
        hits = [kw for kw in keywords if kw.lower() in text]
        if hits:
            matched.append({
                "recommended": r["recommended"],
                "content": r["content"],
                "matched_keywords": hits,
                "votes_up": r["votes_up"],
                "posted_at": r["posted_at"],
            })

    matched.sort(key=lambda r: r["votes_up"], reverse=True)
    neg = sum(1 for r in matched if not r["recommended"])

    return {
        "keyword_match_count": len(matched),
        "match_ratio": round(len(matched) / len(filtered), 3) if filtered else 0,
        "negative_ratio_in_matches": round(neg / len(matched), 3) if matched else 0,
        "top_matches": matched[:10],
    }


def execute_tool(name: str, inputs: dict, game_data: dict) -> dict:
    if name == "get_recent_reviews":
        return tool_get_recent_reviews(
            game_data,
            days_back=inputs.get("days_back", 7),
            sentiment=inputs.get("sentiment", "all"),
            limit=inputs.get("limit", 30),
        )
    elif name == "get_patch_notes":
        return tool_get_patch_notes(game_data, days_back=inputs.get("days_back", 30))
    elif name == "get_sentiment_stats":
        return tool_get_sentiment_stats(game_data, days_back=inputs.get("days_back", 7))
    elif name == "search_by_keyword":
        return tool_search_by_keyword(
            game_data,
            keywords=inputs.get("keywords", []),
            days_back=inputs.get("days_back", 14),
        )
    return {"error": f"알 수 없는 tool: {name}"}


# ── Tool 정의 (Claude Tool Use) ───────────────────────────────────────────────

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
                "limit": {"type": "integer", "description": "반환할 최대 리뷰 수 (기본 30)"},
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


# ── QA Agent Loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 게임 운영 전문 AI 어시스턴트입니다.
Steam 유저 리뷰와 공식 패치노트 데이터를 분석하여 게임 운영자/기획자/마케터의 질문에 답변합니다.

답변 원칙:
1. 데이터에 기반한 근거 있는 분석을 제공한다
2. 구체적인 수치(비율, 건수, 날짜)를 활용한다
3. 운영자가 즉시 실행할 수 있는 액션 아이템을 제안한다
4. 데이터가 부족하면 솔직하게 한계를 언급한다
5. 질문과 동일한 언어로 답변한다 (한국어 질문 → 한국어 답변, 영어 질문 → 영어 답변)"""


async def ask_question(question: str, game_data: dict,
                        client: anthropic.AsyncAnthropic) -> tuple[str, list[str]]:
    """질문을 받아 Tool Use로 데이터를 조회하고 답변을 반환한다."""
    messages = [{"role": "user",
                 "content": f"게임: {game_data['game_name']}\n\n질문: {question}"}]
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
                    result = execute_tool(block.name, block.input, game_data)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            answer = "".join(b.text for b in response.content if hasattr(b, "text"))
            return answer.strip(), tools_used


# ── 데모 & 대화형 모드 ────────────────────────────────────────────────────────

DEMO_QUESTIONS = [
    "요즘 유저 리텐션이 떨어진 것 같아. 데이터를 보고 이유를 분석해줘.",
    "최근 패치 이후 유저 반응이 어떻게 바뀌었어? 패치 전후를 비교해줘.",
    "부정적인 리뷰에서 가장 많이 언급되는 문제가 뭐야? 우선순위를 정해줘.",
]


def fmt_ms(ms: int) -> str:
    return f"{ms/1000:.1f}s" if ms >= 1000 else f"{ms}ms"


def game_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def save_qa_report(game_data: dict, qa_log: list[dict], days_back: int) -> Path:
    """Q&A 결과를 reports/ 폴더에 마크다운으로 저장한다."""
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = game_slug(game_data["game_name"])
    out_path = reports_dir / f"qa-{date_str}-{slug}.md"

    lines = [
        f"# QA Report — {game_data['game_name']}",
        f"> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"수집 기간: 최근 {days_back}일 | "
        f"리뷰 {len(game_data['reviews'])}건 · 뉴스 {len(game_data['news'])}건",
        "",
    ]

    for i, entry in enumerate(qa_log, 1):
        lines += [
            f"## Q{i}. {entry['question']}",
            "",
            entry["answer"],
            "",
            f"*사용된 도구: {', '.join(dict.fromkeys(entry['tools']))} | {fmt_ms(entry['elapsed_ms'])}*",
            "",
            "---",
            "",
        ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


async def run_demo(game_data: dict, client: anthropic.AsyncAnthropic,
                   save: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"  데모 모드 — {game_data['game_name']}")
    print(f"  리뷰 {len(game_data['reviews'])}건 · 뉴스 {len(game_data['news'])}건 수집됨")
    print(f"{'='*60}\n")

    qa_log: list[dict] = []
    for i, q in enumerate(DEMO_QUESTIONS, 1):
        print(f"Q{i}. {q}")
        print("-" * 50)
        t0 = time.monotonic()
        try:
            answer, tools = await ask_question(q, game_data, client)
            elapsed = int((time.monotonic() - t0) * 1000)
            print(answer)
            print(f"\n  [사용된 도구: {', '.join(dict.fromkeys(tools))} | {fmt_ms(elapsed)}]")
            qa_log.append({"question": q, "answer": answer, "tools": tools, "elapsed_ms": elapsed})
        except Exception as e:
            print(f"오류: {e}")
        print()
        await asyncio.sleep(1)

    if save and qa_log:
        path = save_qa_report(game_data, qa_log, game_data["days_back"])
        print(f"\n리포트 저장됨: {path}")


async def run_interactive(game_data: dict, client: anthropic.AsyncAnthropic,
                          save: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"  대화형 모드 — {game_data['game_name']}")
    print(f"  리뷰 {len(game_data['reviews'])}건 · 뉴스 {len(game_data['news'])}건 수집됨")
    print(f"  종료: 'exit' 또는 Ctrl+C")
    print(f"{'='*60}\n")

    qa_log: list[dict] = []
    while True:
        try:
            question = input("질문> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n종료합니다.")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "종료"):
            print("종료합니다.")
            break

        print()
        t0 = time.monotonic()
        try:
            answer, tools = await ask_question(question, game_data, client)
            elapsed = int((time.monotonic() - t0) * 1000)
            print(answer)
            print(f"\n  [사용된 도구: {', '.join(dict.fromkeys(tools))} | {fmt_ms(elapsed)}]")
            qa_log.append({"question": question, "answer": answer, "tools": tools, "elapsed_ms": elapsed})
        except Exception as e:
            print(f"오류: {e}")
        print()

    if save and qa_log:
        path = save_qa_report(game_data, qa_log, game_data["days_back"])
        print(f"\n리포트 저장됨: {path}")


# ── main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="Game LiveOps Advisor — Agent E POC")
    parser.add_argument("--game", type=str, required=True,
                        help="분석할 게임 이름 (Steam 검색)")
    parser.add_argument("--days", type=int, default=7,
                        help="수집할 데이터 기간 (기본 7일)")
    parser.add_argument("--interactive", action="store_true",
                        help="대화형 모드 (미지정 시 데모 모드)")
    parser.add_argument("--save", action="store_true",
                        help="Q&A 결과를 reports/ 폴더에 마크다운으로 저장")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY 미설정")
        sys.exit(1)

    # 게임 검색
    print(f"\nSteam 검색: '{args.game}'")
    game = await search_steam_game(args.game)
    if not game:
        print("검색 결과 없음")
        sys.exit(1)
    print(f"대상 게임: {game['name']} (app_id={game['app_id']})")

    # 데이터 수집
    print(f"최근 {args.days}일 데이터 수집 중...")
    game_data = await fetch_game_data(game["app_id"], game["name"], days_back=args.days)
    print(f"리뷰 {len(game_data['reviews'])}건, 뉴스 {len(game_data['news'])}건 수집 완료")

    if not game_data["reviews"] and not game_data["news"]:
        print("수집된 데이터가 없습니다. --days 값을 늘려보세요.")
        sys.exit(1)

    ai_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    if args.interactive:
        await run_interactive(game_data, ai_client, save=args.save)
    else:
        await run_demo(game_data, ai_client, save=args.save)


if __name__ == "__main__":
    asyncio.run(main())
