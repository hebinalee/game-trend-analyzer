# Developer Log — Game Trend Analyzer

> A chronological record of key design decisions, turning points, and implementation milestones.

---

## Table of Contents

- [2026-04-04 — Project Initialization](#2026-04-04--project-initialization)
- [2026-04-11 — Crawler Replacement: Naver Game Lounge → Steam Community API](#2026-04-11--crawler-replacement-naver-game-lounge--steam-community-api)
- [2026-04-12 — Standalone Report Generator and First Steam Trend Report](#2026-04-12--standalone-report-generator-and-first-steam-trend-report)
- [2026-04-13 — Documentation Improvements](#2026-04-13--documentation-improvements)
- [2026-04-15 — Proactive AI Agent Team Design and Implementation (PR #1)](#2026-04-15--proactive-ai-agent-team-design-and-implementation-pr-1)
- [2026-04-19 — Slack Webhook Integration and API Reliability Fixes (PR #2)](#2026-04-19--slack-webhook-integration-and-api-reliability-fixes-pr-2)
- [2026-04-23 — Custom Game Mode (PR #3)](#2026-04-23--custom-game-mode-pr-3)
- [2026-04-23 — Agent E Design: Introducing the Operator Q&A Service](#2026-04-23--agent-e-design-introducing-the-operator-qa-service)
- [2026-04-24 — Agent E: Live Ops Advisor (PR #4)](#2026-04-24--agent-e-live-ops-advisor-pr-4)
- [2026-05-07 — Game Ops Portal Frontend](#2026-05-07--game-ops-portal-frontend-current-branch-featureportal)
- [2026-06-23 — Multi-Platform Data Source Expansion](#2026-06-23--multi-platform-data-source-expansion-featuremulti-platform-sources)
- [2026-06-28 — Reddit Data Collection Testing & Portal Integration](#2026-06-28--reddit-data-collection-testing--portal-integration-featuremulti-platform)
- [2026-07-02 — Mobile Top 10 Finalized + Google Play & App Store Crawlers Added](#2026-07-02--mobile-top-10-finalized--google-play--app-store-crawlers-added-featuremulti-platform)
- [2026-07-03 — Portal Platform Filter (Steam / Mobile Separation)](#2026-07-03--portal-platform-filter-steam--mobile-separation)
- [2026-07-05 — Frontend UI Complete Overhaul (Production-Grade Upgrade)](#2026-07-05--frontend-ui-complete-overhaul-production-grade-upgrade)
- [2026-07-11 — Service Name Finalized: 게임 동향 기상청 / Game Trend Analyzer (GTA)](#2026-07-11--service-name-finalized-게임-동향-기상청--game-trend-analyzer-gta)
- [Current Status and Open Items](#current-status-and-open-items)

---

## 2026-04-04 — Project Initialization

**Goal:** Build the foundational service to automatically collect and analyze game community trends and deliver reports.

**Implemented:**
- Backend: FastAPI + SQLAlchemy ORM (`Game`, `Post`, `Report` models)
- Crawler: Playwright-based Naver Game Lounge scraper (top 10 games)
- Analysis engine: Sentiment analysis and trend report generation via Claude API
- Scheduler: APScheduler — crawl every 6h, analyze daily at 07:00 KST
- Frontend: React 18 + Vite + TailwindCSS dashboard (with comparison view)
- Infrastructure: Docker Compose integrating PostgreSQL + backend + frontend

---

## 2026-04-11 — Crawler Replacement: Naver Game Lounge → Steam Community API

**Background:** Naver Game Lounge required Playwright for JS rendering, carrying high CSS selector breakage risk. Steam offers official APIs, providing far better stability and scalability.

| Aspect | Naver Game Lounge | Steam Community |
|--------|------------------|----------------|
| Crawling method | Playwright (JS rendering required) | Official REST API |
| Selector breakage risk | High | Low (API-driven) |
| Language | Korean | English (multilingual) |
| Game selection | Manually fixed | Automatable via concurrent players Top 10 |

**Changes:**
- Deleted `crawler/naver_lounge.py` → wrote `crawler/steam_community.py` (httpx-based)
- APIs used: `store.steampowered.com/appreviews/{appid}` (reviews), `api.steampowered.com/ISteamNews/GetNewsForApp/v2/` (patch notes)
- `Game` model: renamed `lounge_id` → `app_id` (Steam App ID, integer)
- Replaced `SEED_GAMES` with 10 popular Steam games (CS2, Dota 2, PUBG, etc.)
- Updated LLM analysis prompt with Steam review/news context and `post_type` field
- Removed Playwright + Chromium dependencies entirely → leaner Docker image

---

## 2026-04-12 — Standalone Report Generator and First Steam Trend Report

**Implemented:**
- `scripts/generate_report.py`: collects Steam reviews/news then calls Claude AI to produce and save an HTML report
- `reports/steam-trend-2026-04-11.html`: first-ever trend analysis report covering 10 popular games
- Created architecture diagram and reflected it in README

---

## 2026-04-13 — Documentation Improvements

- Added sample report section to README
- Replaced htmlpreview.github.io link (connection refused) with `raw.githack.com` for the sample report

---

## 2026-04-15 — Proactive AI Agent Team Design and Implementation (PR #1)

**Background:** The existing service was purely passive — it generated daily reports for humans to read. Game operations staff (marketing, CS, planning, business) found it hard to trace community-side root causes when in-game metrics anomalies appeared.

**Direction:** Evolve into a **proactive AI operations assistant** that detects anomalies first, then automatically pushes root-cause analysis and department-specific action items.

### Agent Team Composition

| Agent | Module | Role |
|-------|--------|------|
| Agent A — Anomaly Detector | `backend/detector/anomaly_detector.py` | Detects sentiment drops, review spikes, keyword surges; classifies severity |
| Agent B — Slack Notifier | `backend/notifier/slack_notifier.py` | Sends Block Kit CRITICAL/WARNING messages; handles retry scheduling |
| Agent C — Action Recommender | `backend/analyzer/action_recommender.py` | Calls Claude API → generates per-department action items (CS, Planning, Marketing, Business) |
| Agent D — Issue Management API & UI | `backend/api/alerts.py` + `frontend/src/pages/Alerts.jsx` | Issue list/detail/status-update API, issue tracking dashboard |

### Detection Logic (Agent A)

| Type | WARNING Threshold | CRITICAL Threshold |
|------|------------------|-------------------|
| `sentiment_drop` | Negative ratio +20%p↑ & currently >50% | +30%p↑ & currently >60% |
| `volume_spike` | Hourly review count 3×↑ | 5×↑ |
| `keyword_alert` | Warning keywords +15%↑ (bug, lag, crash, etc.) | Urgent keywords +10%↑ (refund, server down, hack, etc.) |

- Duplicate alerts for the same game + type are suppressed within a 6-hour window

### Trigger Chain

```
Steam API → Crawler → DB
                       ↓
              [Agent A] Anomaly Detector
                       ↓ anomaly found
          ┌────────────┴─────────────┐
 [Agent C] Action Recommender   [Agent B] Slack Notifier
  (Claude API → dept. actions)   (Webhook → ops team)
          └────────────┬─────────────┘
                  alerts table
                       ↓
          [Agent D] React Issue Dashboard
```

### Specification Documents Created

| File | Purpose |
|------|---------|
| `specs/TEAM.md` | Team charter — mission, 5 operating principles, collaboration protocol |
| `specs/PLAN.md` | Roadmap — milestones, dependency graph |
| `specs/ARCHITECTURE.md` | AS-IS → TO-BE, trigger chain, data contracts |
| `specs/agents/agent_*.md` | Per-agent role spec and implementation checklist |

### POC Pipeline Results (`scripts/poc_pipeline.py`)

| Stage | Result | Duration |
|-------|--------|----------|
| Stage 1 Steam crawling | 10 games, 602 posts (600 reviews + 2 news) | 18.6s |
| Stage 2 LLM analysis | 9 complete, 1 failed (Cyberpunk — empty response) | 161.7s |
| Stage 3 Anomaly detection | 1 alert created (CS2 CRITICAL simulation) | 9ms |
| Stage 4 Action recommendation | CS2 4-department action items generated | 20.2s |
| Stage 5 Slack notification | Skipped (SLACK_WEBHOOK_URL not configured) | — |

---

## 2026-04-19 — Slack Webhook Integration and API Reliability Fixes (PR #2)

**Problem 1 — Steam API Rate Limiting:**
- Increased inter-game delay: 1s → 3s; review-to-news delay: 0.5s → 2s
- Collection count recovered: ~7 posts (mostly 0) → 608 posts

**Problem 2 — Intermittent empty Claude API responses:**
- Added `_claude_call_with_retry()` helper
- Retries up to 3 times on empty response or JSON parse failure (2s → 5s → 10s exponential backoff)

**Slack Webhook Live Integration:**
- Implemented `send_slack_alert()`
  - CRITICAL: full Block Kit format (metrics + summary + top action items)
  - WARNING: concise summary message only
- Verified 2 successful Slack deliveries (1 CRITICAL, 1 WARNING)

---

## 2026-04-23 — Custom Game Mode (PR #3)

**Background:** The service was locked to Steam Top 10. Operators needed the ability to specify any game for targeted analysis.

**Design Decisions:**
- Used Steam Store Search API (`store.steampowered.com/api/storesearch/`) for fuzzy matching — eliminates the need for exact title input
- Used `appdetails` API to extract genres → `GENRE_GAME_MAP` (12 genres, 5–6 curated titles each) for automatic selection of 4 similar games
- Falls back to Action genre if genre data is unavailable

**Usage:**
```bash
python scripts/poc_pipeline.py                    # Default Top 10 mode
python scripts/poc_pipeline.py --game "Elden Ring"  # Custom game mode
```

**Report Layout Changes:**
- Main game: full-width solo placement at the top (★ badge + blue border)
- Similar games: 2-column grid below
- Filename includes main game slug: `poc-pipeline-{date}-{game-slug}.html`

**Other:**
- Added Slack CRITICAL alert screenshot (`docs/slack-alert-critical.png`)
- Separated POC script dependencies: `scripts/requirements.txt`

---

## 2026-04-23 — Agent E Design: Introducing the Operator Q&A Service

**Background:** Agents A–D all operated in push mode — anomaly detected, alert sent. A gap emerged: operators needed to ask questions directly, such as "Why has user retention been dropping lately?" or "Why is the reaction to this patch worse than the last one?" and get answers grounded in the stored review and patch data. This led to the decision to introduce **Agent E** as an on-demand Q&A agent.

**Design Decision — RAG vs Tool Use:**

Added **Agent E** to cover the role not addressed by Agents A–D: answering operators' on-demand questions.

| Aspect | RAG | Tool Use (chosen) |
|--------|-----|------------------|
| Data structure | Suited for unstructured documents | Suited for structured DB/files |
| Time filtering | Indirect | Direct query (`days_back`) |
| Aggregation (ratios, counts) | Not possible | Possible |
| Additional infrastructure | Vector DB required | None |
| Accuracy | Approximate | Exact SQL |
| Extra packages | chromadb, sentence-transformers | None |

→ Date-based precise queries (e.g., "reactions since the last patch") are the core use case, so **Tool Use** was chosen.

**Four Tools Implemented:**

| Tool | Description |
|------|-------------|
| `get_recent_reviews` | Fetch reviews filtered by period and sentiment |
| `get_patch_notes` | Fetch patch notes and official announcements |
| `get_sentiment_stats` | Daily sentiment trend data |
| `search_by_keyword` | Search posts by keyword (costume, balance, etc.) |

**Tool Use Flow:**
1. Operator submits a question
2. Claude selects the necessary tools (0–N calls)
3. Calls among `get_recent_reviews` / `get_patch_notes` / `get_sentiment_stats` / `search_by_keyword`
4. Generates final answer after data collection is complete

**Implementation:**

| File | Role |
|------|------|
| `scripts/qa_pipeline.py` | POC script (3 demo questions auto-run + `--interactive` mode) |
| `backend/analyzer/game_qa.py` | Agent E core logic |
| `backend/schemas/qa.py` | Request/response Pydantic schemas |
| `backend/api/qa.py` | `POST /api/qa` endpoint |

**Usage:**
```bash
# Demo mode (3 preset questions run automatically)
python scripts/qa_pipeline.py --game "Elden Ring"

# Interactive mode
python scripts/qa_pipeline.py --game "Elden Ring" --interactive

# Extended data window
python scripts/qa_pipeline.py --game "Elden Ring" --days 14 --interactive
```

---

## 2026-04-24 — Agent E: Live Ops Advisor (PR #4)

**Background:** Agents A–D all operate in push mode (anomaly detected → automatic alert). What was missing was an on-demand agent that could answer operators' active questions such as "Why are CS2 players requesting so many refunds lately?"

**RAG vs Tool Use Decision:**
- For structured DB data, precise SQL queries outperform vector search
- No additional infrastructure (vector DB) required → **chose Tool Use**

**Four Tools Implemented:**

| Tool | Description |
|------|-------------|
| `get_recent_reviews` | Fetch N most recent reviews |
| `get_patch_notes` | Fetch recent patch notes / official news |
| `get_sentiment_stats` | Query sentiment statistics for a given period |
| `search_by_keyword` | Full-text search of posts by keyword |

**Agent Loop:** Claude selects and executes the necessary tools iteratively until it can produce a final answer (agentic loop).

**Key Changes:**
- Language detection: responds in the same language as the question (Korean → Korean, English → English)
- `--save` flag: exports Q&A session to `reports/qa-{game-slug}-{date}.md` on exit
- Naming refactor: `game_qa.py` → `live_ops_advisor.py`, API route `POST /api/qa` → `POST /api/live-ops-advisor`

---

## 2026-05-07 — Game Ops Portal Frontend (current branch: feature/portal)

**Background:** The original `GameDetail` page was a simple report viewer. With Agent E (Live Ops Advisor) in place, an integrated **operator portal** was needed — combining reports and AI chat in a single view.

**Implemented:**

| Tab | Content |
|-----|---------|
| Tab 1 — Reports | Today's report + sentiment trend chart + competitor comparison in one view |
| Tab 2 — AI Advisor | Live Ops Advisor API chat UI, suggested questions, tool-use badge display |

**Changed Files:**

| File | Change |
|------|--------|
| `frontend/src/api.js` | Added `askLiveOpsAdvisor(gameId, question)` function |
| `frontend/src/components/AdvisorChat.jsx` | New AI advisor chat component |
| `frontend/src/pages/GameDetail.jsx` | Fully restructured into tab layout |

**`/game/:id` Page Structure:**

Composed of a sidebar and a tab selection area.

- **Sidebar:** Game info, tab selector (Reports / AI Advisor)
- **Tab 1 — Reports:**
  - Today's report (sentiment bar, issues, keywords)
  - 7-day sentiment trend chart
  - Competitor comparison (current game auto-included, up to 3 selectable)
- **Tab 2 — AI Advisor:**
  - Empty state: 4 suggested question buttons
  - Chat UI: user/AI message bubbles, tool-use badge display
  - Input: Enter to send, Shift+Enter for newline

---

## 2026-06-23 — Multi-Platform Data Source Expansion (feature/multi-platform-sources)

**Background:** The service previously covered Steam PC games only. To extend coverage to mobile and cross-platform games, a second data source was introduced.

**Platform Source Evaluation:**

Naver Game Lounge was initially considered but rejected in favor of Reddit:

| Aspect | Naver Game Lounge | Reddit (chosen) |
|--------|-----------------|----------------|
| API | Unofficial internal API (breakage risk) | Official OAuth2 API |
| Coverage | Korean games only | Global, all genres |
| Auth | None required | Client ID/Secret (free registration) |
| Data quality | Community posts only | score (upvotes) + comment_count |
| Stability | Low (prior Playwright incident) | High |

→ **Reddit** selected for its official API, global coverage, and active mobile game subreddits.

**Design Decision — Plugin Crawler Architecture:**

| Aspect | Before | After |
|--------|--------|-------|
| Supported platforms | Steam (PC) only | Steam + Reddit (mobile/cross-platform) |
| Crawler structure | Single-module functions | `BaseCrawler` abstract class, plugin pattern |
| Game identifier uniqueness | `app_id` alone | `(platform, app_id)` composite unique |
| Post source | Implicit (Steam-only) | Explicit `source` field |
| LLM prompt | Hardcoded "Steam community" | Dynamic platform label substitution |

**Changed Files:**

| File | Change |
|------|--------|
| `backend/models/game.py` | Added `platform` field; unique constraint changed from `app_id` to `(platform, app_id)` |
| `backend/models/post.py` | Added `source` field; `post_id` length extended from 100 to 150 |
| `backend/database.py` | Added `platform` key to SEED_GAMES, seeded 5 Reddit mobile games, improved `init_db` upsert logic |
| `backend/crawler/base_crawler.py` *(new)* | `BaseCrawler` abstract class with shared DB save logic |
| `backend/crawler/reddit_community.py` *(new)* | Reddit OAuth2 subreddit crawler; classifies posts as news by flair |
| `backend/crawler/steam_community.py` | Refactored to `SteamCommunityCrawler` class; added `source="steam"` to posts |
| `backend/analyzer/llm_analyzer.py` | Multi-platform aware prompt, added `_PLATFORM_LABELS` map |
| `backend/scheduler/jobs.py` | Iterates `_crawlers` list to run all platform crawlers sequentially |
| `backend/schemas/game.py` | Exposed `platform` field in API responses |
| `backend/config.py` | Added `reddit_client_id`, `reddit_client_secret` settings |
| `.env.example` | Added Reddit OAuth2 credential entries |

**Newly Seeded Reddit Games:**

| Game | Subreddit | Genre |
|------|-----------|-------|
| Genshin Impact | r/Genshin_Impact | Mobile/PC RPG |
| Lost Ark | r/lostarkgame | PC MMORPG |
| PUBG Mobile | r/PUBGMobile | Mobile battle royale |
| Clash of Clans | r/ClashOfClans | Mobile strategy |
| Clash Royale | r/ClashRoyale | Mobile card game |

**Reddit Crawler Behavior:**
- Fetches an access token via OAuth2 `client_credentials` (valid for 1 hour)
- Collects up to 100 recent posts from `r/{subreddit}/new`
- Posts with flair containing patch/update/announcement → `post_type="news"`; others → `"community"`
- If `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` are not set, logs a warning and skips silently

**How to Add a New Platform:**
1. Extend `BaseCrawler` from `crawler/base_crawler.py` and implement `crawl_game()`
2. Add `{"platform": "new_platform", ...}` entries to `SEED_GAMES` in `database.py`
3. Register a display label in `_PLATFORM_LABELS` in `analyzer/llm_analyzer.py`
4. Append an instance to the `_crawlers` list in `scheduler/jobs.py`

---

## 2026-06-28 — Reddit Data Collection Testing & Portal Integration (feature/multi-platform)

**Background:** The multi-platform crawler was wired into the scheduler but the manual `trigger-crawl` endpoint only called the Steam crawler, and the frontend had no way to view posts by source or identify which platform a game belonged to.

**Changes:**

| File | Change |
|------|--------|
| `backend/main.py` | `trigger-crawl` now iterates all crawlers (`SteamCommunityCrawler` + `RedditCommunityCrawler`) instead of calling only the Steam function |
| `backend/api/posts.py` *(new)* | `GET /api/posts/{game_id}` — returns collected posts filtered by `source`, `days_back`, `limit`; sorted by engagement (likes + comments) |
| `backend/schemas/report.py` | Added `platform` field to `DashboardSummaryItem` |
| `backend/api/dashboard.py` | Includes `game.platform` in dashboard summary response |
| `frontend/src/api.js` | Added `getPosts(gameId, { source, daysBack, limit })` |
| `frontend/src/components/ReportCard.jsx` | Platform badge (blue = Steam, orange = Reddit) shown below game name |
| `frontend/src/pages/Dashboard.jsx` | Passes `platform` from summary API to `ReportCard` |
| `frontend/src/pages/GameDetail.jsx` | Added "최근 게시글" (Recent Posts) tab with platform filter, period selector, and per-post badges |

**New API Endpoint:**

```
GET /api/posts/{game_id}?source=reddit&days_back=1&limit=50
```

- `source`: `steam` or `reddit` (omit for all)
- `days_back`: 1–30 (default 1)
- `limit`: 1–200 (default 50)
- Response sorted by `like_count + comment_count` descending

**Portal "Recent Posts" Tab (`/game/:id`):**

- Platform filter dropdown (All / Steam / Reddit)
- Period selector (1 / 3 / 7 days)
- Each post shows: source badge, post-type badge (Review / Notice / Community), title, content preview, likes, comments, author, date

---

## 2026-07-02 — Mobile Top 10 Finalized + Google Play & App Store Crawlers Added (feature/multi-platform)

**Background:** Reddit alone only captured community discussions. To collect actual player reviews — equivalent to Steam reviews — Google Play Store and Apple App Store were added as additional data sources. All three sources are unified under a single game entity, producing one combined report per game.

**Mobile Top 10 Finalized:**

Previous 5 games (arbitrarily chosen, included non-mobile Lost Ark) → replaced with top 10 by global MAU + Reddit community activity:

| Game | Google Play Package | App Store ID | Subreddit |
|------|---------------------|-------------|----------|
| Genshin Impact | com.miHoYo.GenshinImpact | 1517783697 | r/Genshin_Impact |
| Clash of Clans | com.supercell.clashofclans | 529479190 | r/ClashOfClans |
| Pokémon GO | com.nianticlabs.pokemongo | 1094591345 | r/pokemongo |
| Brawl Stars | com.supercell.brawlstars | 1229016807 | r/Brawlstars |
| Clash Royale | com.supercell.clashroyale | 1053012308 | r/ClashRoyale |
| PUBG Mobile | com.tencent.ig | 1330123889 | r/PUBGMobile |
| Mobile Legends | com.mobile.legends | 1160056295 | r/MobileLegendsGame |
| Honkai: Star Rail | com.HoYoverse.hkrpgoversea | 6448589051 | r/HonkaiStarRail |
| Wild Rift | com.riotgames.league.wildrift | 1550969885 | r/wildrift |
| Free Fire | com.dts.freefireth | 1300146617 | r/freefire |

**Design Change — Game Entity Structure:**

| Aspect | Before | After |
|--------|--------|-------|
| Mobile game platform value | `"reddit"` | `"mobile"` |
| Source identifiers | Single `app_id` | Separate `reddit_id` · `play_store_id` · `app_store_id` |
| Data sources per game | 1 (Reddit only) | 3 (Reddit + Google Play + App Store) |
| Report | Potentially per-source | Single report per game_id |

**Changed Files:**

| File | Change |
|------|--------|
| `backend/models/game.py` | Added `reddit_id`, `play_store_id`, `app_store_id` fields |
| `backend/models/post.py` | Added `rating: Float` field; `like_count` / `comment_count` made nullable |
| `backend/database.py` | Mobile SEED_GAMES updated: platform="mobile", all 3 store IDs included |
| `backend/crawler/base_crawler.py` | Added `_games_query()` override point |
| `backend/crawler/reddit_community.py` | Changed to platform="mobile" + uses `game.reddit_id` |
| `backend/crawler/google_play.py` *(new)* | `google-play-scraper` based; collects rating + thumbsUpCount |
| `backend/crawler/app_store.py` *(new)* | iTunes RSS based; collects rating (like_count=null) |
| `backend/scheduler/jobs.py` | Added `GooglePlayCrawler`, `AppStoreCrawler` |
| `backend/main.py` | Registered new crawlers in trigger-crawl |
| `backend/requirements.txt` | Added `google-play-scraper==1.2.7` |
| `backend/analyzer/llm_analyzer.py` | Added ★ rating display in post output; unified platform label to "mobile" |

**Data Collected per Source:**

| Source | rating | like_count | comment_count |
|--------|--------|------------|---------------|
| Steam | null | helpful votes | null |
| Reddit | null | upvote score | comment count |
| Google Play | 1.0~5.0 ✅ | thumbsUpCount ✅ | null |
| App Store | 1.0~5.0 ✅ | null | null |

**Post-Deployment Bug Fixes:**

Issues discovered during the first live crawl and analysis run.

| File | Issue | Fix |
|------|-------|-----|
| `backend/schemas/post.py` | `like_count`/`comment_count` declared as non-null `int` → 500 error on API response | Changed to `int \| None`; added `rating` and `source` fields |
| `backend/api/posts.py` | Same nullable issue + ORDER BY crash on NULL columns | Fixed types, switched to `COALESCE`-based sort |
| `backend/analyzer/llm_analyzer.py` | Accessing `game.name` after `rollback()` triggers SQLAlchemy greenlet error | Pre-capture `game_name = game.name` before the try block |
| `backend/analyzer/llm_analyzer.py` | `like_count + comment_count` sort raises TypeError when either is NULL | Changed to `(p.like_count or 0) + (p.comment_count or 0)` |
| `backend/analyzer/llm_analyzer.py` | Claude model ID `claude-sonnet-4-20250514` → 404 Not Found | Updated to `claude-sonnet-4-6` |
| `backend/analyzer/action_recommender.py` | Same outdated model ID | Updated to `claude-sonnet-4-6` |
| `.claude/settings.local.json` | 13 individual curl endpoint allow-rules | Consolidated into 3 wildcard rules (`curl -s "http://localhost:8000/api/*`) |

---

## 2026-07-03 — Portal Platform Filter (Steam / Mobile Separation)

**Background:** With 10 mobile games added alongside the existing 10 Steam titles, the portal began mixing PC and mobile games on every screen. Cross-platform comparison and analysis is not meaningful, so a platform filter was added across the entire portal to let operators focus on one platform at a time.

**Changes:**

| Page | Change |
|------|--------|
| `Dashboard` | Added 전체 / PC(Steam) / 모바일 filter buttons; each button shows the game count for that platform |
| `Alerts` | Platform filter placed as a top-level row; severity tabs and game dropdown sit below with indentation + left border to express the hierarchy visually |
| `Compare` | Platform filter added; switching platform resets selected games and comparison results |
| `ReportCard` | Removed platform badge (replaced by the dashboard filter above) |

**Alerts Filter Hierarchy Design:**

Simply separating rows was not intuitive enough to convey parent-child relationships. The final design uses a label + indentation + `border-l-2` left border to make the hierarchy explicit:

```
Platform                          ← parent label
  [ All ]  [ PC (Steam) ]  [ Mobile ]

│  Filter                         ← child label (indented + left border)
│  [ All / 🚨CRITICAL / ⚠️WARNING / Unread ]   [ Select game ▾ ]
```

**Additional Improvements:**
- Exposed `gamesError` state when `getGames()` fails, preventing silent failures
- Unified game dropdown `value` to `String(g.id)` to match the string-typed `gameFilter` state

---

## 2026-07-05 — Frontend UI Complete Overhaul (Production-Grade Upgrade)

**Background:** The existing portal was a functional but demo-quality layout built on vanilla Tailwind CSS. A full redesign was undertaken to reach production quality on par with products like Linear, Vercel, and Supabase.

**Key Changes:**

| Area | Before | After |
|------|--------|-------|
| Layout | Top text navigation bar | Dark sidebar (240px, desktop) + icon top bar (mobile) |
| Font | System default | Inter (Google Fonts) |
| Icons | Emojis | lucide-react (consistent SVG icon library) |
| Notifications | Browser `alert()` | Toast component (`useToast` hook, slide-in animation) |
| Sentiment colors | Muted sage green / terracotta | Vivid green-500 · slate-400 · red-500 |

**Page-by-page highlights:**

*Dashboard:*
- Added 3-stat summary row: monitored game count, collected data, active issues
- Platform tabs now use icons (Monitor / Smartphone / Layers) with a segmented switcher design
- `ReportCard`: `rounded-2xl`, platform badge, severity label badge, sentiment distribution dot chips

*Issue Tracking:*
- Filter area consolidated into a single `rounded-2xl` card
- `AlertCard`: severity-tinted backgrounds, lucide icon badges, alert type row
- `AlertDetail`: severity gradient header, slide-in panel animation, icon department tabs, Loader2 spinner

*Game Detail:*
- Sidebar tabs now include icons and a platform badge
- `AdvisorChat`: redesigned chat bubbles, Bot avatar, message timestamps
- `TrendChart`: custom tooltip, clean axis styling

**New Files:**

| File | Purpose |
|------|---------|
| `frontend/src/components/Toast.jsx` | `ToastProvider` + `useToast` hook — global toast notification system |
| `frontend/src/components/index.js` | Component barrel exports |

---

## 2026-07-11 — Service Name Finalized: 게임 동향 기상청 / Game Trend Analyzer (GTA)

**Background:** As the service approached production readiness, an official name was needed. A Korean name evoking weather forecasting and an intuitive English name were settled on.

**Rationale:**

| Language | Name | Reason |
|----------|------|--------|
| Korean | **게임 동향 기상청** | "기상청" (meteorological agency) naturally evokes monitoring and forecasting; the public-institution parody blends credibility with humor |
| English | **Game Trend Analyzer (GTA)** | Descriptive and immediately clear; the GTA acronym doubles as an amusing nod to the famous game franchise |

**Changed Files:**

| File | Change |
|------|--------|
| `frontend/index.html` | `<title>` → `게임 동향 기상청 \| Game Trend Analyzer` |
| `frontend/src/App.jsx` | Sidebar logo: `게임 동향 기상청` / `Game Trend Analyzer (GTA)`; mobile top bar updated |
| `frontend/src/pages/Dashboard.jsx` | Page heading → `게임 동향 기상청` |
| `README.md` | Title and service description updated |
| `README-en.md` | Title and service description updated |

---

## Current Status and Open Items

| Item | Status |
|------|--------|
| Steam data collection pipeline | Complete |
| Anomaly detection + Slack notifications | Complete |
| Custom game mode (POC) | Complete |
| Live Ops Advisor (Tool Use) | Complete |
| Game Ops Portal frontend | Complete (feature/portal merged) |
| Multi-platform source expansion | Complete (feature/multi-platform) |
| Reddit portal integration (posts tab + platform badge) | Complete |
| Mobile Top 10 + Google Play / App Store crawlers | Complete |
| Frontend UI complete overhaul (production-grade) | Complete |
| Service name finalized (게임 동향 기상청 / GTA) | Complete |
| Reddit API key setup | Pending (policy page access issue) |
