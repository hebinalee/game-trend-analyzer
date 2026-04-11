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
Steam Review API ─┐
Steam News API   ─┼→ httpx Crawler → PostgreSQL → Claude API (claude-sonnet-4-20250514)
                  ┘                                          ↓
                                       React SPA ← FastAPI (port 8000)
```

**Data flow:**
1. `scheduler/jobs.py` — APScheduler triggers crawl every 6h, analyze daily at 07:00 KST
2. `crawler/steam_community.py` — httpx fetches Steam reviews + news, saves to `posts` table
3. `analyzer/llm_analyzer.py` — Reads yesterday's posts, calls Claude API, upserts into `reports` table
4. FastAPI serves `reports` and `games` to the React frontend

## Key Files

- `backend/crawler/steam_community.py` — Steam API endpoints (`STEAM_REVIEW_URL`, `STEAM_NEWS_URL`); no CSS selectors needed
- `backend/analyzer/llm_analyzer.py` — LLM prompt templates and JSON response parsing
- `backend/database.py` — `SEED_GAMES` list (Steam top 10 with `app_id`) and `init_db()` which creates tables + seeds on first run
- `backend/main.py` — FastAPI app entry point, lifespan (DB init + scheduler start/stop)

## Database Models

- `Game` — 10 seeded Steam games with `app_id` (e.g. `730` for CS2, `570` for Dota 2)
- `Post` — crawled posts; `post_id` is unique (`{app_id}_review_{id}` or `{app_id}_news_{gid}`)
- `Report` — daily LLM analysis per game; unique on `(game_id, report_date)`, upserted on conflict

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/games` | All active games |
| GET | `/api/reports/{game_id}` | Reports (query: `start_date`, `end_date`) |
| GET | `/api/reports/{game_id}/latest` | Latest report |
| GET | `/api/dashboard/summary` | Today's summary for all games |
| GET | `/api/compare` | Compare games (query: `game_ids`, `date`) |
| POST | `/api/admin/trigger-crawl` | Manual crawl trigger |
| POST | `/api/admin/trigger-analyze` | Manual analyze trigger |

## Steam Crawler Notes

- Reviews: `store.steampowered.com/appreviews/{appid}` — no API key required, returns up to 100 recent reviews
- News: `api.steampowered.com/ISteamNews/GetNewsForApp/v2/` — no API key required, returns patch notes and announcements
- Post content is limited to 1000 chars via `crawler/utils.py:clean_text()`
- Random delay of 1–3s between requests is applied via `crawler/utils.py:random_delay()`
- `post_type` field: `"review"` for user reviews, `"news"` for official announcements
