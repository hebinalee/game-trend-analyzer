"""
Team Agent POC — 전체 파이프라인 실행 시뮬레이션
================================================
DB 없이 독립 실행 가능한 End-to-End 데모.

실행 단계:
  Stage 1. Steam API 크롤링 (실제 API 호출)
  Stage 2. Claude LLM 동향 분석 (실제 API 호출)
  Stage 3. 이상 감지 (실제 로직 + CS2 베이스라인 시뮬레이션으로 CRITICAL 감지 시연)
  Stage 4. 대응 제안 생성 (실제 Claude API 호출)
  Stage 5. HTML 리포트 생성

* Stage 3의 baseline은 DB 히스토리 데이터 대신 시뮬레이션 값을 사용합니다.
  실제 서비스에서는 DB에 저장된 이전 크롤링 데이터와 비교합니다.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL  = os.getenv("SLACK_WEBHOOK_URL", "")

# ── 게임 목록 ─────────────────────────────────────────────────────────────────

STEAM_GAMES = [
    {"name": "Counter-Strike 2",    "app_id": "730"},
    {"name": "Dota 2",              "app_id": "570"},
    {"name": "PUBG: BATTLEGROUNDS", "app_id": "578080"},
    {"name": "Elden Ring",          "app_id": "1245620"},
    {"name": "Baldur's Gate 3",     "app_id": "1086940"},
    {"name": "Rust",                "app_id": "252490"},
    {"name": "Cyberpunk 2077",      "app_id": "1091500"},
    {"name": "Valheim",             "app_id": "892970"},
    {"name": "Terraria",            "app_id": "105600"},
    {"name": "Team Fortress 2",     "app_id": "440"},
]

# ── 장르별 인기 게임 큐레이션 ──────────────────────────────────────────────────
# Steam 장르 키 기준. 지정 게임과 같은 장르에서 유사 게임을 선택할 때 사용.

GENRE_GAME_MAP: dict[str, list[dict]] = {
    "Action": [
        {"name": "Hades",                        "app_id": "1145360"},
        {"name": "Sekiro: Shadows Die Twice",     "app_id": "814380"},
        {"name": "Deep Rock Galactic",            "app_id": "548430"},
        {"name": "Monster Hunter: World",         "app_id": "582010"},
        {"name": "Devil May Cry 5",               "app_id": "601150"},
        {"name": "Hollow Knight",                 "app_id": "367520"},
    ],
    "RPG": [
        {"name": "Baldur's Gate 3",               "app_id": "1086940"},
        {"name": "Divinity: Original Sin 2",      "app_id": "435150"},
        {"name": "Dark Souls III",                "app_id": "374320"},
        {"name": "The Witcher 3: Wild Hunt",      "app_id": "292030"},
        {"name": "Cyberpunk 2077",                "app_id": "1091500"},
        {"name": "Elden Ring",                    "app_id": "1245620"},
    ],
    "Strategy": [
        {"name": "Civilization VI",               "app_id": "289070"},
        {"name": "XCOM 2",                        "app_id": "268500"},
        {"name": "Crusader Kings III",            "app_id": "1158310"},
        {"name": "Total War: WARHAMMER III",      "app_id": "1142710"},
        {"name": "Age of Empires IV",             "app_id": "1466860"},
        {"name": "Stellaris",                     "app_id": "281990"},
    ],
    "Simulation": [
        {"name": "Stardew Valley",                "app_id": "413150"},
        {"name": "Cities: Skylines",              "app_id": "255710"},
        {"name": "Planet Zoo",                    "app_id": "703080"},
        {"name": "Kerbal Space Program 2",        "app_id": "954850"},
        {"name": "Two Point Campus",              "app_id": "1649080"},
        {"name": "Farming Simulator 22",          "app_id": "1248130"},
    ],
    "Indie": [
        {"name": "Celeste",                       "app_id": "504230"},
        {"name": "Hades",                         "app_id": "1145360"},
        {"name": "Undertale",                     "app_id": "391540"},
        {"name": "Cuphead",                       "app_id": "268910"},
        {"name": "Vampire Survivors",             "app_id": "1794680"},
        {"name": "Hollow Knight",                 "app_id": "367520"},
    ],
    "Adventure": [
        {"name": "It Takes Two",                  "app_id": "1426210"},
        {"name": "Disco Elysium",                 "app_id": "632470"},
        {"name": "A Plague Tale: Requiem",        "app_id": "1182480"},
        {"name": "Firewatch",                     "app_id": "383870"},
        {"name": "Life is Strange: True Colors",  "app_id": "936790"},
        {"name": "What Remains of Edith Finch",   "app_id": "501300"},
    ],
    "Free to Play": [
        {"name": "Apex Legends",                  "app_id": "1172470"},
        {"name": "Path of Exile",                 "app_id": "238960"},
        {"name": "Warframe",                      "app_id": "230410"},
        {"name": "Lost Ark",                      "app_id": "1599340"},
        {"name": "Genshin Impact",                "app_id": "1971870"},
        {"name": "Dota 2",                        "app_id": "570"},
    ],
    "Massively Multiplayer": [
        {"name": "Lost Ark",                      "app_id": "1599340"},
        {"name": "New World: Aeternum",           "app_id": "1063730"},
        {"name": "Guild Wars 2",                  "app_id": "39210"},
        {"name": "Path of Exile",                 "app_id": "238960"},
        {"name": "Warframe",                      "app_id": "230410"},
    ],
    "Sports": [
        {"name": "Rocket League",                 "app_id": "252950"},
        {"name": "Football Manager 2024",         "app_id": "2252570"},
        {"name": "EA SPORTS FC 24",               "app_id": "2195250"},
        {"name": "NBA 2K24",                      "app_id": "2338770"},
        {"name": "F1 23",                         "app_id": "2108330"},
    ],
    "Racing": [
        {"name": "Forza Horizon 5",               "app_id": "1551360"},
        {"name": "Assetto Corsa Competizione",    "app_id": "805550"},
        {"name": "F1 23",                         "app_id": "2108330"},
        {"name": "DiRT Rally 2.0",                "app_id": "690790"},
        {"name": "Rocket League",                 "app_id": "252950"},
    ],
    "Casual": [
        {"name": "Stardew Valley",                "app_id": "413150"},
        {"name": "PowerWash Simulator",           "app_id": "1290000"},
        {"name": "Unpacking",                     "app_id": "1135690"},
        {"name": "Vampire Survivors",             "app_id": "1794680"},
        {"name": "Goose Goose Duck",              "app_id": "1568590"},
    ],
}

# ── 데이터 컨테이너 ───────────────────────────────────────────────────────────

@dataclass
class Post:
    post_type: str       # review / news
    title: str
    content: str
    votes_up: int = 0

@dataclass
class CrawlResult:
    game: dict
    posts: list[Post]
    duration_ms: int
    error: str = ""

@dataclass
class AnalysisResult:
    game: dict
    analysis: dict
    post_count: int
    duration_ms: int
    error: str = ""

@dataclass
class Alert:
    game_name: str
    severity: str        # CRITICAL / WARNING
    alert_type: str      # sentiment_drop / volume_spike / keyword_alert
    title: str
    detail: dict
    simulated: bool = False   # True이면 POC용 시뮬레이션 데이터
    recommendations: dict = field(default_factory=dict)
    rec_duration_ms: int = 0

@dataclass
class PipelineLog:
    stage: str
    status: str          # ok / skip / error
    message: str
    duration_ms: int = 0

# ── 게임 검색 & 유사 게임 탐색 ────────────────────────────────────────────────

async def search_steam_game(query: str) -> list[dict]:
    """Steam Store Search API로 게임 검색 (퍼지 매칭 지원)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": query, "l": "english", "cc": "US"},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"name": item["name"], "app_id": str(item["id"])} for item in items[:5]]


async def get_game_genres(app_id: str) -> list[str]:
    """Steam appdetails API로 장르 목록 반환."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": app_id, "filters": "genres"},
        )
        resp.raise_for_status()
        data = resp.json().get(app_id, {})
        if not data.get("success"):
            return []
        return [g["description"] for g in data.get("data", {}).get("genres", [])]


def get_similar_games(primary_app_id: str, genres: list[str], limit: int = 4) -> list[dict]:
    """장르 기반 큐레이션에서 primary 게임을 제외한 유사 게임 반환."""
    seen = {primary_app_id}
    candidates: list[dict] = []
    for genre in genres:
        for game in GENRE_GAME_MAP.get(genre, []):
            if game["app_id"] not in seen:
                seen.add(game["app_id"])
                candidates.append(game)
    # 장르 매칭이 없으면 Action 기본값
    if not candidates:
        for game in GENRE_GAME_MAP.get("Action", []):
            if game["app_id"] not in seen:
                candidates.append(game)
    return candidates[:limit]


async def resolve_game_list(query: str) -> tuple[list[dict], str | None]:
    """
    --game 인수를 받아 (게임 목록, primary_app_id) 반환.
    검색 결과 1위를 primary로 확정하고 유사 게임 4개를 추가한다.
    """
    print(f"\n  Steam 검색: '{query}'")
    candidates = await search_steam_game(query)
    if not candidates:
        print("  검색 결과 없음 — top 10 모드로 전환")
        return STEAM_GAMES, None

    primary = candidates[0]
    print(f"  선택된 게임: {primary['name']} (app_id={primary['app_id']})")

    print(f"  장르 조회 중...", end=" ", flush=True)
    genres = await get_game_genres(primary["app_id"])
    print(f"{', '.join(genres) if genres else '장르 정보 없음'}")

    similar = get_similar_games(primary["app_id"], genres, limit=4)
    game_list = [primary] + similar

    print(f"  분석 대상: {primary['name']} (메인) + 유사 게임 {len(similar)}종")
    for g in similar:
        print(f"    └ {g['name']} ({', '.join(genres[:2]) if genres else '-'})")
    print()

    return game_list, primary["app_id"]


# ── Stage 1: 크롤링 ───────────────────────────────────────────────────────────

def clean(text: str, limit: int = 400) -> str:
    import re
    return re.sub(r"\s+", " ", text or "").strip()[:limit]

def extract_json(text: str) -> dict:
    """Claude 응답에서 JSON 객체를 추출한다. 코드블록·잡문자·빈 블록 방어."""
    import re
    text = text.strip()
    # 코드블록 추출
    if "```" in text:
        parts = text.split("```")
        for part in parts[1::2]:
            if part.startswith("json"):
                part = part[4:]
            part = part.strip()
            if not part:          # 빈 코드블록 방어
                continue
            try:
                return json.loads(part)
            except Exception:
                pass
    # 중괄호 범위 추출
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    # 직접 파싱 (실패 시 JSONDecodeError를 호출자에게 전파)
    return json.loads(text)

async def crawl_game(game: dict, days_back: int = 2) -> CrawlResult:
    t0 = time.monotonic()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    posts: list[Post] = []

    async with httpx.AsyncClient(timeout=30) as client:
        # 리뷰
        try:
            resp = await client.get(
                f"https://store.steampowered.com/appreviews/{game['app_id']}",
                params={"json": 1, "language": "all", "num_per_page": 60,
                        "filter": "recent", "review_type": "all", "purchase_type": "all"},
            )
            resp.raise_for_status()
            for r in resp.json().get("reviews", []):
                created = datetime.fromtimestamp(r["timestamp_created"], tz=timezone.utc)
                if created < cutoff:
                    continue
                posts.append(Post(
                    post_type="review",
                    title="Recommended" if r.get("voted_up") else "Not Recommended",
                    content=clean(r.get("review", "")),
                    votes_up=r.get("votes_up", 0),
                ))
        except Exception as e:
            return CrawlResult(game=game, posts=[], duration_ms=0, error=str(e))

        await asyncio.sleep(2)

        # 뉴스
        try:
            resp = await client.get(
                "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
                params={"appid": game["app_id"], "count": 10, "maxlength": 400, "format": "json"},
            )
            resp.raise_for_status()
            for item in resp.json().get("appnews", {}).get("newsitems", []):
                created = datetime.fromtimestamp(item["date"], tz=timezone.utc)
                if created < cutoff:
                    continue
                posts.append(Post(
                    post_type="news",
                    title=clean(item.get("title", ""), 200),
                    content=clean(item.get("contents", "")),
                ))
        except Exception:
            pass

    return CrawlResult(
        game=game, posts=posts,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )

# ── Stage 2: LLM 분석 ─────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = (
    "당신은 게임 운영 전문 애널리스트입니다. "
    "Steam 커뮤니티 데이터를 분석하여 운영자가 즉시 활용할 수 있는 인사이트를 한국어로 제공합니다."
)

ANALYSIS_PROMPT = """Steam '{game_name}' 최근 데이터 {count}건:
(review: 유저 추천/비추천, news: 공식 공지/패치노트)

{posts_text}

아래 JSON 형식으로만 응답하세요.
{{
  "summary": "전체 동향 3~5줄",
  "hot_topics": ["화제1","화제2","화제3"],
  "sentiment": {{"positive":0.0,"negative":0.0,"neutral":0.0}},
  "key_issues": {{"bugs":["버그1"],"requests":["요청1"],"operations":["운영이슈1"]}},
  "trend_keywords": ["키워드1","키워드2","키워드3","키워드4","키워드5"]
}}"""

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]   # 재시도 간격 (초)

async def _claude_call_with_retry(client, *, model, max_tokens, system, messages) -> str:
    """
    Claude API 호출 + 빈 응답 / JSON 파싱 실패 시 최대 MAX_RETRIES회 재시도.
    JSON 파싱 검증까지 재시도 범위에 포함하여 파싱 실패도 재시도한다.
    모든 시도 실패 시 마지막 예외를 raise한다.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            msg = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            text = msg.content[0].text.strip() if msg.content else ""
            if not text:
                raise ValueError("Claude API 빈 응답")
            extract_json(text)   # JSON 파싱 가능 여부 검증 — 실패 시 재시도
            return text
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f" (재시도 {attempt + 1}/{MAX_RETRIES - 1}, {delay}s 대기...)", end="", flush=True)
                await asyncio.sleep(delay)
    raise last_exc


async def analyze_game(crawl: CrawlResult) -> AnalysisResult:
    t0 = time.monotonic()
    posts = crawl.posts
    if len(posts) > 50:
        posts = sorted(posts, key=lambda p: p.votes_up, reverse=True)[:50]

    lines = []
    for i, p in enumerate(posts, 1):
        lines.append(f"[{i}][{p.post_type.upper()}] {p.title}")
        if p.content:
            lines.append(f"    {p.content[:300]}")
        lines.append("")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    text = await _claude_call_with_retry(
        client,
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=ANALYSIS_SYSTEM,
        messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(
            game_name=crawl.game["name"],
            count=len(posts),
            posts_text="\n".join(lines),
        )}],
    )
    analysis = extract_json(text)

    return AnalysisResult(
        game=crawl.game,
        analysis=analysis,
        post_count=len(crawl.posts),
        duration_ms=int((time.monotonic() - t0) * 1000),
    )

# ── Stage 3: 이상 감지 ────────────────────────────────────────────────────────

CRITICAL_KEYWORDS = ["환불","refund","서버 다운","접속 불가","핵","hack","exploit","계정 정지","banned"]
WARNING_KEYWORDS  = ["버그","bug","렉","lag","crash","오류","error","disconnect","튕김"]

def detect_anomalies(crawl: CrawlResult, analysis: AnalysisResult) -> list[Alert]:
    alerts: list[Alert] = []
    posts = crawl.posts
    game_name = crawl.game["name"]
    reviews = [p for p in posts if p.post_type == "review"]
    sentiment = analysis.analysis.get("sentiment", {})
    current_neg = sentiment.get("negative", 0.0)

    # ── 실제 데이터 기반 감지 ──────────────────────────────────────────────────

    # 1. 실제 리뷰에서 Not Recommended 비율 계산
    if reviews:
        real_neg_count = sum(1 for r in reviews if r.title == "Not Recommended")
        real_neg_ratio = real_neg_count / len(reviews)
    else:
        real_neg_ratio = current_neg

    # 2. 키워드 감지
    all_text = " ".join(f"{p.title} {p.content}" for p in posts).lower()
    crit_hits = [kw for kw in CRITICAL_KEYWORDS if kw.lower() in all_text]
    warn_hits  = [kw for kw in WARNING_KEYWORDS  if kw.lower() in all_text]

    if posts:
        crit_ratio = sum(1 for p in posts if any(k.lower() in f"{p.title} {p.content}".lower() for k in CRITICAL_KEYWORDS)) / len(posts)
        warn_ratio = sum(1 for p in posts if any(k.lower() in f"{p.title} {p.content}".lower() for k in WARNING_KEYWORDS)) / len(posts)
    else:
        crit_ratio = warn_ratio = 0.0

    if crit_ratio >= 0.08 and crit_hits:
        alerts.append(Alert(
            game_name=game_name, severity="CRITICAL", alert_type="keyword_alert",
            title=f"[{game_name}] 긴급 키워드 급증: {', '.join(crit_hits[:3])}",
            detail={"matched_keywords": crit_hits, "keyword_ratio": round(crit_ratio, 4), "total_posts": len(posts)},
            simulated=False,
        ))
    elif warn_ratio >= 0.12 and warn_hits:
        alerts.append(Alert(
            game_name=game_name, severity="WARNING", alert_type="keyword_alert",
            title=f"[{game_name}] 경고 키워드 감지: {', '.join(warn_hits[:3])}",
            detail={"matched_keywords": warn_hits, "keyword_ratio": round(warn_ratio, 4), "total_posts": len(posts)},
            simulated=False,
        ))

    # 3. 부정 감성 자체가 높은 경우 WARNING (베이스라인 없어도 절대값으로 판단)
    if real_neg_ratio >= 0.55 and len(reviews) >= 5 and not any(a.alert_type == "sentiment_drop" for a in alerts):
        alerts.append(Alert(
            game_name=game_name, severity="WARNING", alert_type="sentiment_drop",
            title=f"[{game_name}] 높은 부정 리뷰 비율 감지 ({real_neg_ratio:.0%})",
            detail={"current_negative_ratio": round(real_neg_ratio, 4), "current_reviews": len(reviews)},
            simulated=False,
        ))

    return alerts


def inject_demo_alert(crawl: CrawlResult, analysis: AnalysisResult) -> Alert:
    """
    POC 시연용: CS2에 CRITICAL sentiment_drop 시뮬레이션.
    실제 서비스에서는 DB 히스토리와 비교해 자동 생성됩니다.
    """
    reviews = [p for p in crawl.posts if p.post_type == "review"]
    real_neg_count = sum(1 for r in reviews if r.title == "Not Recommended") if reviews else 0
    real_neg_ratio = real_neg_count / len(reviews) if reviews else 0.5

    # 시뮬레이션: 어제는 부정 비율이 낮았다고 가정
    simulated_baseline = max(0.05, real_neg_ratio - 0.35)

    return Alert(
        game_name=crawl.game["name"],
        severity="CRITICAL",
        alert_type="sentiment_drop",
        title=f"[{crawl.game['name']}] 부정 리뷰 비율 급증 ({simulated_baseline:.0%} → {real_neg_ratio:.0%}, +{real_neg_ratio - simulated_baseline:.0%}p) [시뮬레이션]",
        detail={
            "baseline_negative_ratio": round(simulated_baseline, 4),
            "current_negative_ratio": round(real_neg_ratio, 4),
            "diff": round(real_neg_ratio - simulated_baseline, 4),
            "current_reviews": len(reviews),
            "baseline_reviews": int(len(reviews) * 0.8),
            "window_hours": 6,
            "note": "POC 시연: baseline은 DB 히스토리 대신 시뮬레이션 값 사용",
        },
        simulated=True,
    )

# ── Stage 4: 대응 제안 ────────────────────────────────────────────────────────

RECOMMEND_SYSTEM = (
    "당신은 게임 운영 전문 컨설턴트입니다. "
    "감지된 이슈에 대해 각 부서가 즉시 실행 가능한 대응 방안을 한국어로 제안합니다."
)

RECOMMEND_PROMPT = """게임: {game_name}
이슈 유형: {alert_type}
심각도: {severity}
이슈: {title}

감지 데이터:
{detail_text}

아래 JSON 형식으로만 응답하세요.
{{
  "summary": "이슈 원인 추정 및 핵심 대응 방향 2~3줄",
  "cs":        ["CS팀 방안1","방안2","방안3"],
  "planning":  ["기획팀 방안1","방안2","방안3"],
  "marketing": ["마케팅팀 방안1","방안2","방안3"],
  "business":  ["사업팀 방안1","방안2","방안3"]
}}"""

async def generate_recommendations(alert: Alert) -> None:
    t0 = time.monotonic()
    detail_text = "\n".join(
        f"  {k}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in alert.detail.items()
    )
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    text = await _claude_call_with_retry(
        client,
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=RECOMMEND_SYSTEM,
        messages=[{"role": "user", "content": RECOMMEND_PROMPT.format(
            game_name=alert.game_name,
            alert_type=ALERT_TYPE_KR.get(alert.alert_type, alert.alert_type),
            severity=alert.severity,
            title=alert.title,
            detail_text=detail_text,
        )}],
    )
    alert.recommendations = extract_json(text)
    alert.rec_duration_ms = int((time.monotonic() - t0) * 1000)

# ── Stage 5: Slack 알림 ───────────────────────────────────────────────────────

ALERT_TYPE_KR = {
    "sentiment_drop": "부정 리뷰 비율 급증",
    "volume_spike":   "리뷰 볼륨 급증",
    "keyword_alert":  "긴급 키워드 감지",
}

def _slack_blocks_critical(alert: Alert) -> list:
    """CRITICAL 알림용 Block Kit — 지표 + 상위 1개 추천"""
    recs = alert.recommendations or {}
    top_rec = ""
    for dept in ("cs", "planning", "marketing", "business"):
        items = recs.get(dept, [])
        if items:
            dept_label = {"cs": "CS팀", "planning": "기획팀",
                          "marketing": "마케팅팀", "business": "사업팀"}[dept]
            top_rec = f"*{dept_label}* {items[0]}"
            break

    detail_lines = "\n".join(
        f"• *{k}*: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in alert.detail.items() if k != "note"
    )
    sim_note = "  _(POC 시뮬레이션)_" if alert.simulated else ""

    sim_suffix = " [시뮬레이션]" if alert.simulated else ""
    return [
        {"type": "header", "text": {"type": "plain_text",
            "text": f"🚨 CRITICAL — {alert.game_name}{sim_suffix}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{alert.title}*{sim_note}\n_{ALERT_TYPE_KR.get(alert.alert_type, alert.alert_type)}_"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": detail_lines}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*📋 요약*\n{recs.get('summary', '—')}"}},
        *([ {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*💡 우선 대응*\n{top_rec}"}} ] if top_rec else []),
        {"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"Game Trend Analyzer · POC Pipeline · {datetime.now().strftime('%Y-%m-%d %H:%M KST')}"}]},
    ]

def _slack_blocks_warning(alert: Alert) -> list:
    """WARNING 알림용 Block Kit — 요약만"""
    return [
        {"type": "header", "text": {"type": "plain_text",
            "text": f"⚠️ WARNING — {alert.game_name}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{alert.title}*\n_{ALERT_TYPE_KR.get(alert.alert_type, alert.alert_type)}_"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"Game Trend Analyzer · POC Pipeline · {datetime.now().strftime('%Y-%m-%d %H:%M KST')}"}]},
    ]

async def send_slack_alert(alert: Alert) -> tuple[bool, str]:
    """Slack Incoming Webhook으로 알림 전송. (성공여부, 에러메시지) 반환."""
    if not SLACK_WEBHOOK_URL:
        return False, "SLACK_WEBHOOK_URL 미설정"

    blocks = (_slack_blocks_critical(alert) if alert.severity == "CRITICAL"
              else _slack_blocks_warning(alert))
    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
            if resp.status_code == 200 and resp.text == "ok":
                return True, ""
            return False, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, str(e)


# ── Stage 6: HTML 리포트 빌더 ─────────────────────────────────────────────────

def fmt_ms(ms: int) -> str:
    return f"{ms/1000:.1f}s" if ms >= 1000 else f"{ms}ms"

def severity_badge(sev: str, simulated: bool = False) -> str:
    colors = {"CRITICAL": "#f85149", "WARNING": "#d29922", "INFO": "#3fb950"}
    c = colors.get(sev, "#8b949e")
    label = f"{sev}{'  [시뮬레이션]' if simulated else ''}"
    return f'<span style="background:{c};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:700">{label}</span>'

def recommendations_html(recs: dict) -> str:
    if not recs:
        return '<p style="color:#8b949e;font-size:0.85rem">대응 방안 없음</p>'
    dept_labels = {"cs": "CS팀", "planning": "기획팀", "marketing": "마케팅팀", "business": "사업팀"}
    dept_colors = {"cs": "#58a6ff", "planning": "#3fb950", "marketing": "#d29922", "business": "#bc8cff"}
    html = ""
    if recs.get("summary"):
        html += f'<p style="color:#adbac7;font-size:0.88rem;margin-bottom:12px;line-height:1.6">{recs["summary"]}</p>'
    for key, label in dept_labels.items():
        items = recs.get(key, [])
        if not items:
            continue
        color = dept_colors[key]
        lis = "".join(f"<li>{item}</li>" for item in items)
        html += f'''
        <div style="margin-bottom:10px">
          <strong style="color:{color};font-size:0.8rem">{label}</strong>
          <ul style="padding-left:18px;margin-top:4px;color:#adbac7;font-size:0.85rem;line-height:1.7">{lis}</ul>
        </div>'''
    return html

def alert_card_html(alert: Alert) -> str:
    sev_colors = {"CRITICAL": "#f8514933", "WARNING": "#d2992233"}
    border_colors = {"CRITICAL": "#f85149", "WARNING": "#d29922"}
    bg = sev_colors.get(alert.severity, "#2d333b")
    border = border_colors.get(alert.severity, "#444c56")
    detail_items = "".join(
        f'<tr><td style="color:#8b949e;padding:3px 12px 3px 0;font-size:0.82rem">{k}</td>'
        f'<td style="color:#e6edf3;font-size:0.82rem">{", ".join(v) if isinstance(v, list) else v}</td></tr>'
        for k, v in alert.detail.items() if k != "note"
    )
    note = alert.detail.get("note", "")

    return f'''
    <div style="background:{bg};border:1px solid {border};border-radius:10px;padding:18px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        {severity_badge(alert.severity, alert.simulated)}
        <span style="color:#8b949e;font-size:0.82rem">{ALERT_TYPE_KR.get(alert.alert_type, alert.alert_type)}</span>
        {"" if not alert.rec_duration_ms else f'<span style="color:#8b949e;font-size:0.78rem;margin-left:auto">추천 생성 {fmt_ms(alert.rec_duration_ms)}</span>'}
      </div>
      <p style="color:#e6edf3;font-size:0.9rem;font-weight:600;margin-bottom:10px">{alert.title}</p>
      {"" if not note else f'<p style="color:#d29922;font-size:0.8rem;margin-bottom:8px">⚠ {note}</p>'}
      <table style="margin-bottom:14px">{detail_items}</table>
      <div style="border-top:1px solid #30363d;padding-top:12px">
        <div style="color:#8b949e;font-size:0.75rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:8px">부서별 대응 방안</div>
        {recommendations_html(alert.recommendations)}
      </div>
    </div>'''

def game_section_html(ar: AnalysisResult, cr: CrawlResult, alerts: list[Alert], is_primary: bool = False) -> str:
    a = ar.analysis
    thumb = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{ar.game['app_id']}/header.jpg"
    pos = int(a.get("sentiment", {}).get("positive", 0) * 100)
    neg = int(a.get("sentiment", {}).get("negative", 0) * 100)
    neu = 100 - pos - neg

    reviews = [p for p in cr.posts if p.post_type == "review"]
    news    = [p for p in cr.posts if p.post_type == "news"]

    tags = "".join(
        f'<span style="background:#1f6feb33;color:#58a6ff;border:1px solid #1f6feb66;border-radius:12px;padding:2px 10px;font-size:0.8rem">{t}</span>'
        for t in a.get("hot_topics", [])
    )
    kws = "".join(
        f'<span style="background:#2d333b;color:#adbac7;border-radius:4px;padding:2px 8px;font-size:0.8rem">{k}</span>'
        for k in a.get("trend_keywords", [])
    )

    issues = a.get("key_issues", {})
    def issue_group(items, label, color):
        if not items: return ""
        lis = "".join(f"<li>{i}</li>" for i in items)
        return f'<div style="margin-bottom:8px"><strong style="color:{color};font-size:0.82rem">{label}</strong><ul style="padding-left:16px;margin-top:3px;color:#adbac7;font-size:0.83rem">{lis}</ul></div>'

    issues_html = (
        issue_group(issues.get("bugs", []),       "🐛 버그",     "#f85149") +
        issue_group(issues.get("requests", []),   "💡 요청사항", "#3fb950") +
        issue_group(issues.get("operations", []), "⚙️ 운영이슈", "#d29922")
    )

    alerts_html = ""
    if alerts:
        alerts_html = f'''
        <div style="margin-top:18px">
          <div style="color:#8b949e;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">🔔 감지된 이슈 ({len(alerts)}건)</div>
          {"".join(alert_card_html(al) for al in alerts)}
        </div>'''

    primary_badge = (
        '<span style="background:#1f6feb;color:#fff;border-radius:8px;'
        'padding:2px 10px;font-size:0.75rem;font-weight:700;margin-left:8px">★ 메인 게임</span>'
        if is_primary else ""
    )
    border_style = "border:2px solid #1f6feb" if is_primary else "border:1px solid #30363d"

    return f'''
    <div style="background:#161b22;{border_style};border-radius:10px;padding:20px;break-inside:avoid">
      <div style="display:flex;gap:14px;margin-bottom:14px;align-items:flex-start">
        <img src="{thumb}" style="width:120px;height:56px;object-fit:cover;border-radius:6px;flex-shrink:0" onerror="this.style.display='none'">
        <div style="flex:1">
          <h2 style="color:#e6edf3;font-size:1.05rem">{ar.game["name"]}{primary_badge}</h2>
          <div style="color:#8b949e;font-size:0.78rem;margin-top:3px">
            리뷰 {len(reviews)}건 &nbsp;·&nbsp; 뉴스 {len(news)}건 &nbsp;·&nbsp;
            크롤 {fmt_ms(cr.duration_ms)} &nbsp;·&nbsp; 분석 {fmt_ms(ar.duration_ms)}
          </div>
        </div>
      </div>
      <p style="color:#adbac7;font-size:0.88rem;margin-bottom:14px;white-space:pre-line">{a.get("summary","")}</p>
      <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px">
        <div style="width:{pos}%;background:#3fb950" title="긍정 {pos}%"></div>
        <div style="width:{neu}%;background:#8b949e" title="중립 {neu}%"></div>
        <div style="width:{neg}%;background:#f85149" title="부정 {neg}%"></div>
      </div>
      <div style="display:flex;gap:12px;font-size:0.78rem;margin-bottom:14px">
        <span style="color:#3fb950">긍정 {pos}%</span>
        <span style="color:#8b949e">중립 {neu}%</span>
        <span style="color:#f85149">부정 {neg}%</span>
      </div>
      <div style="font-size:0.75rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">핫토픽</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">{tags}</div>
      <div style="font-size:0.75rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">트렌드 키워드</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:{"14px" if issues_html else "0"}">{kws}</div>
      {"" if not issues_html else f'<div style="font-size:0.75rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">주요 이슈</div>' + issues_html}
      {alerts_html}
    </div>'''

def pipeline_log_html(logs: list[PipelineLog]) -> str:
    rows = ""
    for log in logs:
        icon = {"ok": "✅", "skip": "⏭", "error": "❌"}.get(log.status, "•")
        color = {"ok": "#3fb950", "skip": "#8b949e", "error": "#f85149"}.get(log.status, "#adbac7")
        rows += f'''
        <tr>
          <td style="padding:6px 12px 6px 0;color:#8b949e;font-size:0.83rem;white-space:nowrap">{log.stage}</td>
          <td style="padding:6px 12px 6px 0">{icon}</td>
          <td style="padding:6px 12px 6px 0;color:{color};font-size:0.83rem">{log.message}</td>
          <td style="padding:6px 0;color:#8b949e;font-size:0.83rem;text-align:right">{fmt_ms(log.duration_ms) if log.duration_ms else "-"}</td>
        </tr>'''
    return f'<table style="width:100%;border-collapse:collapse">{rows}</table>'

def build_report(
    crawls: list[CrawlResult],
    analyses: list[AnalysisResult],
    alerts_by_game: dict[str, list[Alert]],
    logs: list[PipelineLog],
    run_date: str,
    total_ms: int,
    primary_app_id: str | None = None,
) -> str:
    all_alerts = [a for lst in alerts_by_game.values() for a in lst]
    critical_count = sum(1 for a in all_alerts if a.severity == "CRITICAL")
    warning_count  = sum(1 for a in all_alerts if a.severity == "WARNING")
    total_posts    = sum(len(c.posts) for c in crawls)

    # primary 게임을 최상단으로 정렬
    sorted_analyses = sorted(
        analyses,
        key=lambda ar: (0 if ar.game["app_id"] == primary_app_id else 1),
    )

    primary_section = ""
    similar_sections = ""
    for ar in sorted_analyses:
        cr = next((c for c in crawls if c.game["app_id"] == ar.game["app_id"]), None)
        if not cr:
            continue
        game_alerts = alerts_by_game.get(ar.game["name"], [])
        is_primary = (primary_app_id is not None and ar.game["app_id"] == primary_app_id)
        html_block = game_section_html(ar, cr, game_alerts, is_primary=is_primary)
        if is_primary:
            primary_section = html_block
        else:
            similar_sections += html_block

    # primary가 있으면 전폭 단독 배치, 유사 게임은 2단 그리드
    if primary_app_id and primary_section:
        sections = f'''
        <div style="margin-bottom:20px">{primary_section}</div>
        <div style="columns:2 480px;column-gap:20px">{similar_sections}</div>
        '''
    else:
        sections = f'<div style="columns:2 480px;column-gap:20px">{similar_sections}</div>'

    mode_badge = (
        f'<span style="background:#1f6feb33;color:#58a6ff;border:1px solid #1f6feb66;'
        f'border-radius:12px;padding:3px 12px;font-size:0.82rem">Custom Game Mode</span>'
        if primary_app_id else
        f'<span style="background:#1f6feb33;color:#58a6ff;border:1px solid #1f6feb66;'
        f'border-radius:12px;padding:3px 12px;font-size:0.82rem">Top 10 Mode</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Team Agent POC — {run_date}</title>
<style>
  * {{ box-sizing:border-box;margin:0;padding:0 }}
  body {{ font-family:'Segoe UI',sans-serif;background:#0e1117;color:#c9d1d9;line-height:1.6 }}
  a {{ color:#58a6ff }}
</style>
</head>
<body>

<!-- 헤더 -->
<div style="background:#161b22;border-bottom:1px solid #30363d;padding:28px 36px">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
    <h1 style="color:#e6edf3;font-size:1.7rem">🤖 Team Agent POC</h1>
    <span style="background:#238636;color:#fff;border-radius:12px;padding:3px 12px;font-size:0.82rem">End-to-End Pipeline</span>
    {mode_badge}
  </div>
  <p style="color:#8b949e;font-size:0.9rem">
    실행일: {run_date} &nbsp;·&nbsp;
    총 소요: {fmt_ms(total_ms)} &nbsp;·&nbsp;
    수집: {total_posts}건 &nbsp;·&nbsp;
    분석 게임: {len(analyses)}종 &nbsp;·&nbsp;
    감지된 이슈: <span style="color:#f85149;font-weight:700">CRITICAL {critical_count}</span> &nbsp;
                 <span style="color:#d29922;font-weight:700">WARNING {warning_count}</span>
  </p>
</div>

<!-- 파이프라인 실행 로그 -->
<div style="max-width:900px;margin:28px auto 0;padding:0 36px">
  <h2 style="color:#e6edf3;font-size:1.1rem;margin-bottom:14px">📋 파이프라인 실행 로그</h2>
  <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px">
    {pipeline_log_html(logs)}
  </div>

  <!-- 아키텍처 다이어그램 -->
  <h2 style="color:#e6edf3;font-size:1.1rem;margin:28px 0 14px">🔗 트리거 체인</h2>
  <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px;font-family:monospace;font-size:0.85rem;color:#adbac7;line-height:2">
    Steam API &nbsp;──▶&nbsp; <span style="color:#58a6ff">Stage 1: Crawler</span> &nbsp;──▶&nbsp; Posts<br>
    Posts &nbsp;──▶&nbsp; <span style="color:#3fb950">Stage 2: LLM Analyzer</span> &nbsp;──▶&nbsp; Report (sentiment / topics / issues)<br>
    Posts &nbsp;──▶&nbsp; <span style="color:#d29922">Stage 3: Anomaly Detector</span> &nbsp;──▶&nbsp; Alert (CRITICAL / WARNING)<br>
    Alert &nbsp;──▶&nbsp; <span style="color:#bc8cff">Stage 4: Action Recommender</span> &nbsp;──▶&nbsp; 부서별 대응 방안 (Claude API)<br>
    Alert + Recs &nbsp;──▶&nbsp; <span style="color:#f85149">Stage 5: Slack Notifier</span> &nbsp;──▶&nbsp; Slack 채널 전송 (CRITICAL: Block Kit 풀포맷 / WARNING: 요약)
  </div>
</div>

<!-- 게임별 결과 -->
<div style="max-width:1600px;margin:28px auto;padding:0 36px">
  {sections}
</div>

<div style="text-align:center;padding:24px;color:#8b949e;font-size:0.8rem;border-top:1px solid #30363d">
  Game Trend Analyzer — Team Agent POC &nbsp;·&nbsp; Powered by Steam API + Anthropic Claude
  &nbsp;·&nbsp; Agent A (Detector) + Agent C (Recommender) + Agent B (Notifier sim) + Agent D (UI)
</div>

</body>
</html>"""

# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Game Trend Analyzer — POC Pipeline")
    parser.add_argument("--game", type=str, default=None,
                        help="분석할 게임 이름 (미지정 시 Steam Top 10 기본 실행)")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY 미설정")
        sys.exit(1)

    run_date = datetime.now().strftime("%Y-%m-%d")
    t_total  = time.monotonic()
    logs: list[PipelineLog] = []

    print(f"\n{'='*60}")
    print(f"  Team Agent POC — {run_date}")
    print(f"{'='*60}")

    # 게임 목록 결정
    if args.game:
        game_list, primary_app_id = await resolve_game_list(args.game)
        logs.append(PipelineLog("Game Discovery", "ok",
                                f"메인: {game_list[0]['name']} / 유사 게임 {len(game_list)-1}종"))
    else:
        game_list, primary_app_id = STEAM_GAMES, None
        print(f"\n  모드: Top 10 기본 실행\n")

    # Stage 1: 크롤링
    print("▶ Stage 1: Steam API 크롤링")
    t0 = time.monotonic()
    crawls: list[CrawlResult] = []
    for game in game_list:
        print(f"  [{game['name']}] 수집 중...", end=" ", flush=True)
        cr = await crawl_game(game)
        crawls.append(cr)
        reviews = len([p for p in cr.posts if p.post_type == "review"])
        news    = len([p for p in cr.posts if p.post_type == "news"])
        print(f"리뷰 {reviews}건 / 뉴스 {news}건 ({fmt_ms(cr.duration_ms)})")
        await asyncio.sleep(3)

    stage1_ms = int((time.monotonic() - t0) * 1000)
    total_posts = sum(len(c.posts) for c in crawls)
    logs.append(PipelineLog("Stage 1 · Crawler", "ok",
                            f"{len(crawls)}개 게임 크롤링 완료 — 총 {total_posts}건 수집", stage1_ms))
    print(f"  → 완료 ({fmt_ms(stage1_ms)}, 총 {total_posts}건)\n")

    # Stage 2: LLM 분석
    print("▶ Stage 2: Claude LLM 동향 분석")
    t0 = time.monotonic()
    analyses: list[AnalysisResult] = []
    for cr in crawls:
        if not cr.posts:
            logs.append(PipelineLog(f"  {cr.game['name']}", "skip", "수집 데이터 없음"))
            continue
        print(f"  [{cr.game['name']}] 분석 중...", end=" ", flush=True)
        try:
            ar = await analyze_game(cr)
            analyses.append(ar)
            s = ar.analysis.get("sentiment", {})
            print(f"긍정 {s.get('positive',0):.0%} / 부정 {s.get('negative',0):.0%} ({fmt_ms(ar.duration_ms)})")
        except Exception as e:
            print(f"오류: {e}")
            logs.append(PipelineLog(f"  {cr.game['name']}", "error", str(e)))

    stage2_ms = int((time.monotonic() - t0) * 1000)
    logs.append(PipelineLog("Stage 2 · LLM Analyzer", "ok",
                            f"{len(analyses)}개 게임 분석 완료", stage2_ms))
    print(f"  → 완료 ({fmt_ms(stage2_ms)})\n")

    # Stage 3: 이상 감지
    print("▶ Stage 3: 이상 감지")
    t0 = time.monotonic()
    alerts_by_game: dict[str, list[Alert]] = {}

    for ar in analyses:
        cr = next(c for c in crawls if c.game["app_id"] == ar.game["app_id"])
        detected = detect_anomalies(cr, ar)
        if detected:
            alerts_by_game[ar.game["name"]] = detected
            for al in detected:
                print(f"  [{al.severity}] {al.game_name}: {al.alert_type}")

    # CRITICAL 시뮬레이션 주입 (POC 시연)
    # 커스텀 모드: primary 게임 / 기본 모드: CS2
    sim_app_id = primary_app_id if primary_app_id else "730"
    sim_crawl    = next((c for c in crawls    if c.game["app_id"] == sim_app_id), None)
    sim_analysis = next((a for a in analyses  if a.game["app_id"] == sim_app_id), None)
    if sim_crawl and sim_analysis:
        demo_alert = inject_demo_alert(sim_crawl, sim_analysis)
        existing = alerts_by_game.get(sim_crawl.game["name"], [])
        existing = [a for a in existing if a.alert_type != "sentiment_drop"]
        alerts_by_game[sim_crawl.game["name"]] = [demo_alert] + existing
        print(f"  [CRITICAL 시뮬레이션] {sim_crawl.game['name']}: sentiment_drop (POC 데모)")

    all_alerts = [a for lst in alerts_by_game.values() for a in lst]
    stage3_ms = int((time.monotonic() - t0) * 1000)
    logs.append(PipelineLog("Stage 3 · Anomaly Detector", "ok",
                            f"Alert {len(all_alerts)}건 생성 (CRITICAL {sum(1 for a in all_alerts if a.severity=='CRITICAL')} / WARNING {sum(1 for a in all_alerts if a.severity=='WARNING')})",
                            stage3_ms))
    print(f"  → 완료: {len(all_alerts)}건 감지 ({fmt_ms(stage3_ms)})\n")

    # Stage 4: 대응 제안
    print("▶ Stage 4: 대응 제안 생성 (Claude API)")
    t0 = time.monotonic()
    for al in all_alerts:
        print(f"  [{al.game_name}] {al.alert_type} 대응 방안 생성 중...", end=" ", flush=True)
        try:
            await generate_recommendations(al)
            print(f"완료 ({fmt_ms(al.rec_duration_ms)})")
        except Exception as e:
            print(f"오류: {e}")

    stage4_ms = int((time.monotonic() - t0) * 1000)
    logs.append(PipelineLog("Stage 4 · Action Recommender", "ok",
                            f"{len(all_alerts)}건 대응 방안 생성 완료", stage4_ms))
    print(f"  → 완료 ({fmt_ms(stage4_ms)})\n")

    # Stage 5: Slack 알림
    print("▶ Stage 5: Slack 알림 전송")
    t0 = time.monotonic()
    slack_ok = slack_fail = 0
    if not SLACK_WEBHOOK_URL:
        logs.append(PipelineLog("Stage 5 · Slack Notifier", "skip",
                                "SLACK_WEBHOOK_URL 미설정 — 스킵"))
        print("  → 스킵 (SLACK_WEBHOOK_URL 미설정)\n")
    else:
        for al in all_alerts:
            print(f"  [{al.severity}] {al.game_name} 알림 전송 중...", end=" ", flush=True)
            ok, err = await send_slack_alert(al)
            if ok:
                slack_ok += 1
                print("전송 완료 ✅")
            else:
                slack_fail += 1
                print(f"실패 ❌ ({err})")
        stage5_ms = int((time.monotonic() - t0) * 1000)
        logs.append(PipelineLog("Stage 5 · Slack Notifier", "ok" if slack_fail == 0 else "error",
                                f"전송 {slack_ok}건 성공 / {slack_fail}건 실패", stage5_ms))
        print(f"  → 완료: {slack_ok}건 전송 ({fmt_ms(stage5_ms)})\n")

    # 리포트 생성
    print("▶ Stage 6: HTML 리포트 생성")
    total_ms = int((time.monotonic() - t_total) * 1000)
    html = build_report(crawls, analyses, alerts_by_game, logs, run_date, total_ms,
                        primary_app_id=primary_app_id)

    out_dir  = Path(__file__).parent.parent / "reports"
    out_dir.mkdir(exist_ok=True)
    if primary_app_id and game_list:
        # 게임 이름을 파일명에 사용 가능한 형태로 변환 (소문자, 공백→하이픈, 특수문자 제거)
        import re
        game_slug = re.sub(r"[^\w\s-]", "", game_list[0]["name"].lower())
        game_slug = re.sub(r"\s+", "-", game_slug.strip())
        out_path = out_dir / f"poc-pipeline-{run_date}-{game_slug}.html"
    else:
        out_path = out_dir / f"poc-pipeline-{run_date}.html"
    out_path.write_text(html, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  리포트 저장: {out_path}")
    print(f"  총 소요 시간: {fmt_ms(total_ms)}")
    print(f"  수집: {total_posts}건 | 분석: {len(analyses)}종 | Alert: {len(all_alerts)}건")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
