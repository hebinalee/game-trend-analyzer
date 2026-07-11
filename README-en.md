[![한국어](https://img.shields.io/badge/언어-한국어-blue)](README.md)
[![English](https://img.shields.io/badge/Language-English-blue)](README-en.md)

# Game Trend Analyzer (GTA)
### 게임 동향 기상청

A live ops dashboard that collects and analyzes reviews, community posts, and store data across 10 Steam PC games and 10 mobile games — from Steam, Reddit, Google Play, and App Store — giving game operators, designers, and marketers an at-a-glance view of community trends.

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3-06B6D4?logo=tailwindcss&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_API-Sonnet_4-D97757?logo=anthropic&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-Alerts-4A154B?logo=slack&logoColor=white)

## Requirements

- Docker & Docker Compose
- Anthropic API Key

## Getting Started

```bash
# 1. Configure environment variables
cp .env.example .env
# Open .env and fill in ANTHROPIC_API_KEY and other values

# 2. Start all services
docker-compose up --build

# 3. Access
# Dashboard:  http://localhost:3000
# Swagger UI: http://localhost:8000/docs
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | gametrend |
| `POSTGRES_PASSWORD` | PostgreSQL password | changeme |
| `POSTGRES_DB` | PostgreSQL database name | gametrend_db |
| `DATABASE_URL` | DB connection URL | postgresql://... |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `CRAWL_INTERVAL_HOURS` | Crawl interval (hours) | 6 |
| `ANALYZE_INTERVAL_HOURS` | Analysis interval (hours) | 24 |

## Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/games` | List all games |
| `GET /api/reports/{game_id}` | Reports for a specific game |
| `GET /api/reports/{game_id}/latest` | Latest report |
| `GET /api/dashboard/summary` | Dashboard summary |
| `GET /api/compare` | Compare games |
| `POST /api/admin/trigger-crawl` | Manual crawl trigger |
| `POST /api/admin/trigger-analyze` | Manual analysis trigger |

## System Architecture

![Architecture](docs/assets/architecture.png)

## Slack Alert Example

A CRITICAL alert automatically sent to the team channel when an anomaly is detected.

![Slack Alert](docs/assets/slack-alert-critical.png)

## Sample Reports

The [`reports/`](./reports/) folder contains real output reports from actual runs.

| Date | Type | Link |
|------|------|------|
| 2026-04-11 | Trend Report | [View rendered page →](https://raw.githack.com/hebinalee/game-trend-analyzer/master/reports/steam-trend-2026-04-11.html) |
| 2026-04-19 | Team Agent POC (Slay the Spire 2) | [View rendered page →](https://raw.githack.com/hebinalee/game-trend-analyzer/master/reports/poc-pipeline-2026-04-19-slay-the-spire-2.html) |

> **Trend Report**
> ```bash
> python scripts/generate_report.py
> # Output: reports/steam-trend-YYYY-MM-DD.html
> ```
>
> **Team Agent POC**
> ```bash
> # Install dependencies (first time only)
> pip install -r scripts/requirements.txt
>
> # Top 10 default mode
> python scripts/poc_pipeline.py
> # Output: reports/poc-pipeline-YYYY-MM-DD.html
>
> # Custom game mode (main game + similar genre analysis)
> python scripts/poc_pipeline.py --game "Elden Ring"
> # Output: reports/poc-pipeline-YYYY-MM-DD-elden-ring.html
> ```

## Collected Data

| Type | Source | Content |
|------|--------|---------|
| `review` | Steam Review API | User recommendations/rejections + review text |
| `news` | Steam News API | Official patch notes and update announcements |

## Schedule

- Crawling: Runs automatically every 6 hours (with an immediate first run 1 minute after app start)
- Analysis: Runs automatically every day at 07:00 KST

## Development History

Key design decisions and development progress are documented in the log below.

[Developer Log →](docs/history/en.md)
