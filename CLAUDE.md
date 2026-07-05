# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Service

```bash
# 환경변수 설정 (ANTHROPIC_API_KEY 필수)
cp .env.example .env

# 전체 서비스 실행
docker-compose up --build

# 대시보드: http://localhost:3000
# Swagger UI: http://localhost:8000/docs
```

## Local Development

**Backend** (Python 3.11 + FastAPI):
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

**Frontend** (React 18 + Vite):
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
npm run build
```

## Architecture

```
Steam Review/News API ─┐
Reddit (subreddit)    ─┼→ httpx Crawler → PostgreSQL → Claude API (claude-sonnet-4-6)
Google Play Store     ─┤                                          ↓
App Store             ─┘              Anomaly Detector → Alert → Slack
                                                                   ↓
                                           React SPA ← FastAPI (port 8000)
```

**Data flow:**
1. `scheduler/jobs.py` — APScheduler triggers crawl every 6h, analyze daily at 07:00 KST
2. Crawlers fetch platform-specific data and save to `posts` table:
   - `crawler/steam_community.py` — Steam reviews + news (PC)
   - `crawler/reddit_community.py` — Reddit posts via API (PC + mobile)
   - `crawler/google_play.py` — Google Play reviews (mobile)
   - `crawler/app_store.py` — App Store reviews (mobile)
3. `detector/anomaly_detector.py` — detects sentiment_drop / volume_spike / keyword_alert → creates `Alert`
4. `analyzer/action_recommender.py` — fills `Alert.recommendations` via Claude API
5. `notifier/slack_notifier.py` — sends CRITICAL/WARNING alerts to Slack
6. `analyzer/llm_analyzer.py` — daily report per game → upserts into `reports` table
7. FastAPI serves all data to the React frontend

## Key Files

- `backend/crawler/steam_community.py` — Steam Review + News API (no key required)
- `backend/crawler/reddit_community.py` — Reddit JSON API (`/r/{subreddit}/new.json`)
- `backend/crawler/google_play.py` — Google Play review scraper (Playwright)
- `backend/crawler/app_store.py` — App Store RSS feed parser
- `backend/crawler/base_crawler.py` — `BaseCrawler` abstract class; all crawlers inherit from this
- `backend/analyzer/llm_analyzer.py` — LLM prompt templates and JSON response parsing
- `backend/database.py` — `SEED_GAMES` list (Steam 10 + mobile 10) and `init_db()`
- `backend/main.py` — FastAPI app entry point, lifespan (DB init + scheduler start/stop)

## Database Models

- `Game` — 20 seeded games (`platform`: `"steam"` or `"mobile"`); unique on `(platform, app_id)`; mobile games have `reddit_id`, `play_store_id`, `app_store_id` fields
- `Post` — crawled posts; `source` field indicates origin (`steam_review`, `reddit`, `google_play`, `app_store`); `rating` is nullable (1–5 scale for store reviews)
- `Report` — daily LLM analysis per game; unique on `(game_id, report_date)`, upserted on conflict
- `Alert` — anomaly alerts; `severity` (`CRITICAL`/`WARNING`/`INFO`), `status` (`new`/`acknowledged`/`resolved`), `recommendations` JSON

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/games` | All active games |
| GET | `/api/reports/{game_id}` | Reports (query: `start_date`, `end_date`) |
| GET | `/api/reports/{game_id}/latest` | Latest report |
| GET | `/api/dashboard/summary` | Today's summary for all games |
| GET | `/api/compare` | Compare games (query: `game_ids`, `date`) |
| GET | `/api/alerts` | Alert list (query: `game_id`, `severity`, `status`, `limit`) |
| GET | `/api/alerts/{alert_id}` | Alert detail with recommendations |
| PATCH | `/api/alerts/{alert_id}/status` | Update alert status |
| GET | `/api/alerts/unread-count` | Unread CRITICAL/WARNING count |
| POST | `/api/live-ops-advisor` | Ask LiveOps Advisor (Tool Use agent) |
| POST | `/api/admin/trigger-crawl` | Manual crawl trigger |
| POST | `/api/admin/trigger-analyze` | Manual analyze trigger |
| POST | `/api/admin/trigger-detect` | Manual anomaly detection trigger |

## Specs & Design Docs

설계 문서는 `specs/` 폴더에 있다. 새 기능 작업 전 반드시 참조한다.

- `specs/ARCHITECTURE.md` — 전체 아키텍처, 데이터 계약, 감지 임계값, 파일 맵
- `specs/PLAN.md` — 마일스톤, 스프린트 계획, 리스크
- `specs/TEAM.md` — 팀 운영 원칙, 에이전트 간 협업 프로토콜
- `specs/agents/agent_a_detector.md` — 이상 감지 엔진 명세
- `specs/agents/agent_b_notifier.md` — Slack 알림 엔진 명세
- `specs/agents/agent_c_recommender.md` — 대응 제안 엔진 명세
- `specs/agents/agent_d_api_ui.md` — 이슈 관리 API·UI 명세
- `specs/agents/agent_e_live_ops_advisor.md` — LiveOps Advisor 명세

## Crawler Notes

**Steam** (PC): `store.steampowered.com/appreviews/{appid}` + `api.steampowered.com/ISteamNews/` — no API key required

**Reddit**: `reddit.com/r/{subreddit}/new.json` — no API key required; `reddit_id` field on `Game` stores subreddit name

**Google Play**: Playwright headless browser scraper; `play_store_id` field on `Game` stores package name

**App Store**: RSS feed `itunes.apple.com/rss/customerreviews/id={app_store_id}/json`; `app_store_id` field on `Game`

공통:
- Post content limited to 1000 chars via `crawler/utils.py:clean_text()`
- Random delay 1–3s via `crawler/utils.py:random_delay()`
- `source` field identifies origin; `post_type`: `"review"` or `"news"`
