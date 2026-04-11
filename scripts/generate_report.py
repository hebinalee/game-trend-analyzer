"""
Steam 게임 트렌드 리포트 생성 스크립트
- Steam API에서 인기 게임 10종의 리뷰/뉴스 수집
- Claude API로 동향 분석
- HTML 리포트 파일로 저장
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import anthropic
from dotenv import load_dotenv

# .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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

SYSTEM_PROMPT = (
    "당신은 게임 운영 전문 애널리스트입니다. "
    "Steam 커뮤니티의 유저 리뷰와 공식 뉴스를 분석하여 "
    "운영자/기획자/마케터가 즉시 활용할 수 있는 인사이트를 한국어로 제공합니다."
)

USER_PROMPT_TEMPLATE = """다음은 Steam '{game_name}' 게임의 최근 데이터 {count}건입니다.
(review: 유저 추천/비추천 리뷰, news: 공식 패치노트/공지)

{posts_text}

위 데이터를 분석하여 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요.
리뷰의 Recommended/Not Recommended 여부를 sentiment 산정에 반영하세요.

{{
  "summary": "전체 동향 3~5줄 요약",
  "hot_topics": ["화제1", "화제2", "화제3"],
  "sentiment": {{"positive": 0.0, "negative": 0.0, "neutral": 0.0}},
  "key_issues": {{
    "bugs": ["버그1"],
    "requests": ["요청사항1"],
    "operations": ["운영이슈1"]
  }},
  "trend_keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
}}"""


def clean_text(text: str | None, max_length: int = 500) -> str:
    if not text:
        return ""
    import re
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


async def fetch_reviews(app_id: str, days_back: int = 3) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    params = {"json": 1, "language": "all", "num_per_page": 50,
              "filter": "recent", "review_type": "all", "purchase_type": "all"}
    posts = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"https://store.steampowered.com/appreviews/{app_id}", params=params
            )
            resp.raise_for_status()
            for review in resp.json().get("reviews", []):
                created = datetime.fromtimestamp(review["timestamp_created"], tz=timezone.utc)
                if created < cutoff:
                    continue
                posts.append({
                    "type": "review",
                    "title": "Recommended" if review.get("voted_up") else "Not Recommended",
                    "content": clean_text(review.get("review", "")),
                    "votes_up": review.get("votes_up", 0),
                })
        except Exception as e:
            print(f"  [reviews] {app_id} 오류: {e}")
    return posts


async def fetch_news(app_id: str, days_back: int = 3) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    params = {"appid": app_id, "count": 10, "maxlength": 500, "format": "json"}
    posts = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/", params=params
            )
            resp.raise_for_status()
            for item in resp.json().get("appnews", {}).get("newsitems", []):
                created = datetime.fromtimestamp(item["date"], tz=timezone.utc)
                if created < cutoff:
                    continue
                posts.append({
                    "type": "news",
                    "title": clean_text(item.get("title", ""), 200),
                    "content": clean_text(item.get("contents", "")),
                    "votes_up": 0,
                })
        except Exception as e:
            print(f"  [news] {app_id} 오류: {e}")
    return posts


async def analyze(game_name: str, posts: list[dict]) -> dict:
    if len(posts) > 50:
        posts = sorted(posts, key=lambda p: p["votes_up"], reverse=True)[:50]

    lines = []
    for i, p in enumerate(posts, 1):
        lines.append(f"[{i}][{p['type'].upper()}] {p['title']}")
        if p["content"]:
            lines.append(f"    {p['content'][:300]}")
        lines.append("")
    posts_text = "\n".join(lines)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(
            game_name=game_name, count=len(posts), posts_text=posts_text
        )}],
    )
    text = message.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def sentiment_bar(sentiment: dict) -> str:
    pos = int(sentiment.get("positive", 0) * 100)
    neu = int(sentiment.get("neutral", 0) * 100)
    neg = 100 - pos - neu
    return f"""
    <div class="sentiment-bar">
      <div class="seg positive" style="width:{pos}%" title="긍정 {pos}%"></div>
      <div class="seg neutral"  style="width:{neu}%" title="중립 {neu}%"></div>
      <div class="seg negative" style="width:{neg}%" title="부정 {neg}%"></div>
    </div>
    <div class="sentiment-legend">
      <span class="pos-text">긍정 {pos}%</span>
      <span class="neu-text">중립 {neu}%</span>
      <span class="neg-text">부정 {neg}%</span>
    </div>"""


def build_html(results: list[dict], run_date: str) -> str:
    cards = ""
    for r in results:
        game = r["game"]
        data = r["analysis"]
        thumb = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{game['app_id']}/header.jpg"

        hot_topics = "".join(f'<span class="tag">{t}</span>' for t in data.get("hot_topics", []))
        keywords   = "".join(f'<span class="kw">{k}</span>'  for k in data.get("trend_keywords", []))

        issues = data.get("key_issues", {})
        def issue_list(items, label, cls):
            if not items:
                return ""
            lis = "".join(f"<li>{i}</li>" for i in items)
            return f'<div class="issue-group"><strong class="{cls}">{label}</strong><ul>{lis}</ul></div>'

        issues_html = (
            issue_list(issues.get("bugs", []),       "🐛 버그",     "bug") +
            issue_list(issues.get("requests", []),   "💡 요청사항", "req") +
            issue_list(issues.get("operations", []), "⚙️ 운영이슈", "ops")
        )

        cards += f"""
        <div class="card">
          <div class="card-header">
            <img src="{thumb}" alt="{game['name']}" class="thumb">
            <div class="card-title">
              <h2>{game['name']}</h2>
              <div class="post-count">수집 데이터: {r['post_count']}건</div>
            </div>
          </div>
          <div class="summary">{data.get('summary','')}</div>
          {sentiment_bar(data.get('sentiment', {}))}
          <div class="section-label">핫토픽</div>
          <div class="tags">{hot_topics}</div>
          <div class="section-label">트렌드 키워드</div>
          <div class="keywords">{keywords}</div>
          {'<div class="section-label">주요 이슈</div>' + issues_html if issues_html else ''}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Steam 게임 트렌드 리포트 — {run_date}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0e1117; color: #c9d1d9; line-height: 1.6; }}
  header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 24px 32px; }}
  header h1 {{ font-size: 1.6rem; color: #e6edf3; }}
  header p  {{ color: #8b949e; font-size: 0.9rem; margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 20px; padding: 28px 32px; max-width: 1600px; margin: 0 auto; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }}
  .card-header {{ display: flex; gap: 14px; margin-bottom: 14px; }}
  .thumb {{ width: 120px; height: 56px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }}
  .card-title h2 {{ font-size: 1.05rem; color: #e6edf3; }}
  .post-count {{ font-size: 0.78rem; color: #8b949e; margin-top: 2px; }}
  .summary {{ font-size: 0.88rem; color: #adbac7; margin-bottom: 14px; white-space: pre-line; }}
  .sentiment-bar {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }}
  .seg {{ height: 100%; }}
  .positive {{ background: #3fb950; }}
  .neutral  {{ background: #8b949e; }}
  .negative {{ background: #f85149; }}
  .sentiment-legend {{ display: flex; gap: 12px; font-size: 0.78rem; margin-bottom: 14px; }}
  .pos-text {{ color: #3fb950; }} .neu-text {{ color: #8b949e; }} .neg-text {{ color: #f85149; }}
  .section-label {{ font-size: 0.75rem; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; margin: 10px 0 6px; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }}
  .tag {{ background: #1f6feb33; color: #58a6ff; border: 1px solid #1f6feb66; border-radius: 12px; padding: 2px 10px; font-size: 0.8rem; }}
  .keywords {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .kw {{ background: #2d333b; color: #adbac7; border-radius: 4px; padding: 2px 8px; font-size: 0.8rem; }}
  .issue-group {{ margin-top: 8px; font-size: 0.85rem; }}
  .issue-group ul {{ padding-left: 18px; margin-top: 4px; }}
  .issue-group li {{ margin-bottom: 2px; color: #adbac7; }}
  .bug {{ color: #f85149; }} .req {{ color: #3fb950; }} .ops {{ color: #d29922; }}
  footer {{ text-align: center; padding: 24px; color: #8b949e; font-size: 0.8rem; border-top: 1px solid #30363d; margin-top: 12px; }}
</style>
</head>
<body>
<header>
  <h1>🎮 Steam 게임 트렌드 리포트</h1>
  <p>생성일: {run_date} &nbsp;|&nbsp; 분석 기간: 최근 3일 &nbsp;|&nbsp; 대상: Steam 인기 게임 10종 &nbsp;|&nbsp; Powered by Claude AI</p>
</header>
<div class="grid">{cards}</div>
<footer>Game Trend Analyzer &nbsp;·&nbsp; Powered by Steam API + Anthropic Claude</footer>
</body>
</html>"""


async def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    run_date = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Steam 게임 트렌드 리포트 생성 ({run_date}) ===\n")

    results = []
    for game in STEAM_GAMES:
        print(f"[{game['name']}] 데이터 수집 중...")
        reviews = await fetch_reviews(game["app_id"])
        news    = await fetch_news(game["app_id"])
        posts   = reviews + news
        print(f"  → 리뷰 {len(reviews)}건 / 뉴스 {len(news)}건")

        if not posts:
            print(f"  → 수집된 데이터 없음, 건너뜀\n")
            continue

        print(f"  → Claude 분석 중...")
        try:
            analysis = await analyze(game["name"], posts)
            results.append({"game": game, "analysis": analysis, "post_count": len(posts)})
            print(f"  → 완료\n")
        except Exception as e:
            print(f"  → 분석 오류: {e}\n")

    if not results:
        print("분석 결과가 없습니다.")
        sys.exit(1)

    # 리포트 저장
    out_dir = Path(__file__).parent.parent / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"steam-trend-{run_date}.html"
    out_path.write_text(build_html(results, run_date), encoding="utf-8")
    print(f"리포트 저장 완료: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
