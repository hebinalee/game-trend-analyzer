# Game Trend Analyzer

Steam 인기 게임 10개를 대상으로 매일 유저 리뷰와 공식 뉴스를 수집·분석하여
게임 운영자/기획자/마케터가 커뮤니티 동향을 한눈에 파악할 수 있는 대시보드 서비스입니다.

## 요구사항

- Docker & Docker Compose
- Anthropic API Key

## 실행 방법

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 등 값을 수정

# 2. 전체 서비스 실행
docker-compose up --build

# 3. 접속
# 대시보드:  http://localhost:3000
# Swagger UI: http://localhost:8000/docs
```

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `POSTGRES_USER` | PostgreSQL 사용자 | gametrend |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 | changeme |
| `POSTGRES_DB` | PostgreSQL DB명 | gametrend_db |
| `DATABASE_URL` | DB 연결 URL | postgresql://... |
| `ANTHROPIC_API_KEY` | Anthropic API 키 | - |
| `CRAWL_INTERVAL_HOURS` | 크롤링 주기 (시간) | 6 |
| `ANALYZE_INTERVAL_HOURS` | 분석 주기 (시간) | 24 |

## 주요 API

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/games` | 전체 게임 목록 |
| `GET /api/reports/{game_id}` | 특정 게임 리포트 목록 |
| `GET /api/reports/{game_id}/latest` | 최신 리포트 |
| `GET /api/dashboard/summary` | 대시보드 요약 |
| `GET /api/compare` | 게임 비교 |
| `POST /api/admin/trigger-crawl` | 수동 크롤링 트리거 |
| `POST /api/admin/trigger-analyze` | 수동 분석 트리거 |

## 아키텍처

![Architecture](docs/architecture.png)

## 수집 데이터

| 유형 | 출처 | 내용 |
|------|------|------|
| `review` | Steam 리뷰 API | 유저 추천/비추천 + 리뷰 텍스트 |
| `news` | Steam 뉴스 API | 공식 패치노트, 업데이트 공지 |

## 스케줄

- 크롤링: 매 6시간 자동 실행 (앱 시작 1분 후 즉시 1회 실행)
- 분석: 매일 오전 7시 (KST) 자동 실행
