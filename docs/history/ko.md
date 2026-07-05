# 개발자 로그 — Game Trend Analyzer

> 프로젝트의 주요 설계 결정, 전환점, 구현 과정을 날짜순으로 기록한 로그입니다.

---

## 목차

- [2026-04-04 — 프로젝트 초기 구축](#2026-04-04--프로젝트-초기-구축)
- [2026-04-11 — 크롤러 교체: 네이버 게임 라운지 → Steam Community API](#2026-04-11--크롤러-교체-네이버-게임-라운지--steam-community-api)
- [2026-04-12 — 독립 실행형 리포트 생성기 추가 및 첫 Steam 트렌드 리포트](#2026-04-12--독립-실행형-리포트-생성기-추가-및-첫-steam-트렌드-리포트)
- [2026-04-13 — 문서 개선](#2026-04-13--문서-개선)
- [2026-04-15 — 능동적 AI 에이전트 팀 설계 및 구현 (PR #1)](#2026-04-15--능동적-ai-에이전트-팀-설계-및-구현-pr-1)
- [2026-04-19 — Slack 웹훅 연동 및 API 안정성 개선 (PR #2)](#2026-04-19--slack-웹훅-연동-및-api-안정성-개선-pr-2)
- [2026-04-23 — 커스텀 게임 모드 추가 (PR #3)](#2026-04-23--커스텀-게임-모드-추가-pr-3)
- [2026-04-23 — Agent E 설계: 운영자 Q&A 서비스 도입 결정](#2026-04-23--agent-e-설계-운영자-qa-서비스-도입-결정)
- [2026-04-24 — Agent E: Live Ops Advisor 추가 (PR #4)](#2026-04-24--agent-e-live-ops-advisor-추가-pr-4)
- [2026-05-07 — Game Ops Portal 프론트엔드](#2026-05-07--game-ops-portal-프론트엔드)
- [2026-06-23 — 멀티 플랫폼 데이터 소스 확장](#2026-06-23--멀티-플랫폼-데이터-소스-확장-featuremulti-platform-sources)
- [2026-06-28 — Reddit 데이터 수집 테스트 및 포털 통합](#2026-06-28--reddit-데이터-수집-테스트-및-포털-통합-featuremulti-platform)
- [2026-07-02 — 모바일 게임 Top 10 확정 및 Google Play · App Store 크롤러 추가](#2026-07-02--모바일-게임-top-10-확정-및-google-play--app-store-크롤러-추가-featuremulti-platform)
- [2026-07-03 — 포탈 플랫폼 필터 추가 (Steam / 모바일 분리)](#2026-07-03--포탈-플랫폼-필터-추가-steam--모바일-분리)
- [2026-07-05 — 프론트엔드 UI 전면 개편 (프로덕션 수준 업그레이드)](#2026-07-05--프론트엔드-ui-전면-개편-프로덕션-수준-업그레이드)
- [현재 상태 및 미결 사항](#현재-상태-및-미결-사항)

---

## 2026-04-04 — 프로젝트 초기 구축

**목표:** 게임 커뮤니티 동향을 자동으로 수집·분석해 리포트를 제공하는 서비스 뼈대 구축.

**구현 내용:**
- 백엔드: FastAPI + SQLAlchemy ORM (`Game`, `Post`, `Report` 모델)
- 크롤러: Playwright 기반 네이버 게임 라운지 수집기 (인기 게임 10종)
- 분석 엔진: Claude API를 활용한 감성 분석 및 트렌드 리포트 생성
- 스케줄러: APScheduler — 6시간 주기 크롤링, 매일 07:00 KST 분석 자동화
- 프론트엔드: React 18 + Vite + TailwindCSS 대시보드 (비교 뷰 포함)
- 인프라: Docker Compose로 PostgreSQL + 백엔드 + 프론트엔드 통합 실행

---

## 2026-04-11 — 크롤러 교체: 네이버 게임 라운지 → Steam Community API

**배경:** 네이버 게임 라운지는 JS 렌더링이 필요해 Playwright 의존성이 크고, 선택자 변경 리스크가 높았다. 반면 Steam은 공식 API를 제공하므로 안정성과 확장성이 훨씬 높다.

| 항목 | 네이버 게임 라운지 | Steam Community |
|------|------------------|----------------|
| 크롤링 방식 | Playwright (JS 렌더링 필수) | 공식 REST API |
| 선택자 깨짐 위험 | 높음 | 낮음 (API 위주) |
| 언어 | 한국어 | 영어 (다국어) |
| 게임 선정 | 수동 고정 | 동시접속자 Top 10 자동화 가능 |

**변경 내용:**
- `crawler/naver_lounge.py` 삭제 → `crawler/steam_community.py` 신규 작성 (httpx 기반)
- 활용 API: `store.steampowered.com/appreviews/{appid}` (리뷰), `api.steampowered.com/ISteamNews/GetNewsForApp/v2/` (패치노트)
- `Game` 모델의 `lounge_id` 필드 → `app_id` (Steam App ID, 정수형)로 변경
- `SEED_GAMES`를 Steam 인기 게임 10종으로 교체 (CS2, Dota 2, PUBG 등)
- LLM 분석 프롬프트에 Steam 리뷰/뉴스 맥락 및 `post_type` 표시 추가
- Playwright + Chromium 의존성 전면 제거 → Docker 이미지 경량화

---

## 2026-04-12 — 독립 실행형 리포트 생성기 추가 및 첫 Steam 트렌드 리포트

**구현 내용:**
- `scripts/generate_report.py`: Steam API로 리뷰/뉴스 수집 후 Claude AI 분석, HTML 리포트 자동 저장
- `reports/steam-trend-2026-04-11.html`: 인기 게임 10종 동향 분석 리포트 (최초 실행본)
- 아키텍처 다이어그램 작성 및 README 반영

---

## 2026-04-13 — 문서 개선

- README에 샘플 리포트 섹션 추가
- htmlpreview.github.io 연결 거부 문제로 인해 샘플 리포트 링크를 `raw.githack.com`으로 교체

---

## 2026-04-15 — 능동적 AI 에이전트 팀 설계 및 구현 (PR #1)

**배경:** 기존 서비스는 "매일 리포트를 생성해두면 사람이 보는" 수동적 구조. 게임 운영(마케팅, CS, 기획, 사업) 담당자가 인게임 지표 이상을 발견하더라도 커뮤니티 원인을 직접 파악하기 어려웠다.

**전환 방향:** 이상 징후를 AI가 먼저 감지하고, 원인 분석 + 부서별 대응 방안을 자동으로 밀어주는 **능동적 AI 업무 비서**로 고도화.

### 팀 에이전트 구성

| 에이전트 | 담당 모듈 | 역할 |
|---------|----------|------|
| Agent A — 이상 감지 엔진 | `backend/detector/anomaly_detector.py` | sentiment 급변 / 리뷰 폭증 / 키워드 급증 탐지, 심각도 분류 |
| Agent B — Slack 알림 엔진 | `backend/notifier/slack_notifier.py` | Block Kit 기반 CRITICAL/WARNING 메시지 전송, 재시도 스케줄 |
| Agent C — 대응 제안 엔진 | `backend/analyzer/action_recommender.py` | Claude API 호출 → CS/기획/마케팅/사업 부서별 대응 방안 생성 |
| Agent D — 이슈 관리 API & UI | `backend/api/alerts.py` + `frontend/src/pages/Alerts.jsx` | 이슈 목록/상세/상태 변경 API, 이슈 트래킹 대시보드 |

### 감지 로직 (Agent A)

| 타입 | WARNING 조건 | CRITICAL 조건 |
|------|-------------|--------------|
| `sentiment_drop` | 부정 비율 +20%p↑ & 현재 50%↑ | +30%p↑ & 현재 60%↑ |
| `volume_spike` | 시간당 리뷰 수 3배↑ | 5배↑ |
| `keyword_alert` | 경고 키워드 15%↑ (버그·렉·crash 등) | 긴급 키워드 10%↑ (환불·서버다운·핵 등) |

- 동일 게임·타입 알림은 6시간 내 중복 생성 방지

### 트리거 체인

```
Steam API → Crawler → DB
                       ↓
              [Agent A] Anomaly Detector
                       ↓ 이슈 감지
          ┌────────────┴─────────────┐
 [Agent C] Action Recommender   [Agent B] Slack Notifier
  (Claude API → 부서별 대응)     (Webhook → 담당자 수신)
          └────────────┬─────────────┘
                  alerts 테이블
                       ↓
          [Agent D] React 이슈 대시보드
```

### 설계 문서 신규 생성

| 파일 | 목적 |
|------|------|
| `specs/TEAM.md` | 팀 헌장 — 미션, 운영 원칙 5개, 협업 프로토콜 |
| `specs/PLAN.md` | 로드맵 — 마일스톤, 의존성 그래프 |
| `specs/ARCHITECTURE.md` | AS-IS → TO-BE, 트리거 체인, 데이터 계약 |
| `specs/agents/agent_*.md` | 에이전트별 역할 명세 및 체크리스트 |

### POC 파이프라인 실행 결과 (`scripts/poc_pipeline.py`)

| Stage | 결과 | 소요 |
|-------|------|------|
| Stage 1 Steam 크롤링 | 10게임, 602건 (리뷰 600 + 뉴스 2) | 18.6s |
| Stage 2 LLM 동향 분석 | 9종 완료, 1종 실패 (Cyberpunk — 빈 응답) | 161.7s |
| Stage 3 이상 감지 | Alert 1건 생성 (CS2 CRITICAL 시뮬레이션) | 9ms |
| Stage 4 대응 제안 | CS2 4부서 대응 방안 생성 | 20.2s |
| Stage 5 Slack 알림 | SLACK_WEBHOOK_URL 미설정으로 스킵 | — |

---

## 2026-04-19 — Slack 웹훅 연동 및 API 안정성 개선 (PR #2)

**문제 1 — Steam API Rate Limiting:**
- 게임 간 딜레이 1s → 3s, 리뷰→뉴스 사이 0.5s → 2s로 증가
- 수집 건수: 7건(대부분 0) → 608건으로 정상화

**문제 2 — Claude API 빈 응답 간헐적 발생:**
- `_claude_call_with_retry()` 헬퍼 추가
- 빈 응답 또는 JSON 파싱 실패 시 최대 3회 재시도 (2s → 5s → 10s 지수 백오프)

**Slack 웹훅 실전 연동:**
- `send_slack_alert()` 함수 구현
  - CRITICAL: Block Kit 풀포맷 (지표 + 요약 + 상위 대응 방안)
  - WARNING: 요약 메시지만 전송
- Slack 전송 2건 성공 확인 (CRITICAL 1건, WARNING 1건)

---

## 2026-04-23 — 커스텀 게임 모드 추가 (PR #3)

**배경:** 기존 서비스는 Steam Top 10 게임으로 고정. 운영자가 원하는 게임을 직접 지정해 분석할 수 있는 기능이 필요했다.

**설계 결정:**
- Steam Store Search API(`store.steampowered.com/api/storesearch/`)로 퍼지 매칭 검색 → 완전 매칭 문제 해결
- `appdetails` API로 장르 추출 → `GENRE_GAME_MAP`(12개 장르, 장르별 5~6종 큐레이션) 기반 유사 게임 4종 자동 선택
- 장르 정보 없을 시 Action 기본값 사용

**실행 방식:**
```bash
python scripts/poc_pipeline.py                    # Top 10 기본 모드
python scripts/poc_pipeline.py --game "Elden Ring"  # 커스텀 모드
```

**리포트 레이아웃 변경:**
- 메인 게임: 최상단 전폭 단독 배치 (★ 뱃지 + 파란 테두리)
- 유사 게임: 하단 2단 그리드 배치
- 파일명에 메인 게임 슬러그 반영: `poc-pipeline-{날짜}-{game-slug}.html`

**기타:**
- Slack CRITICAL 알림 실제 전송 결과 스크린샷 추가 (`docs/slack-alert-critical.png`)
- POC 스크립트 전용 의존성 분리: `scripts/requirements.txt`

---

## 2026-04-23 — Agent E 설계: 운영자 Q&A 서비스 도입 결정

**배경:** 기존 Agent A~D는 모두 이상 감지 → 자동 알림의 Push 방식이었다. 운영자가 "요즘 유저 리텐션이 떨어진 이유가 뭐야?", "저번 패치 대비 이번 패치 반응이 왜 안좋아?" 같은 질문을 직접 던지면 DB에 저장된 리뷰·패치 데이터를 근거로 답변해주는 On-demand Q&A 에이전트의 필요성이 제기됐다. 이를 위해 **Agent E**를 신규 추가하기로 결정.

**설계 결정 — RAG vs Tool Use:**

기존 Agent A~D로 커버되지 않는 역할(운영자 능동 질문 답변)을 위해 **Agent E** 를 신규 추가.

| 항목 | RAG | Tool Use (선택) |
|------|-----|----------------|
| 데이터 구조 | 비정형 문서에 적합 | 구조화된 DB/파일에 적합 |
| 시간 필터링 | 간접적 | 직접 쿼리 (`days_back`) |
| 집계 (비율·건수) | 불가 | 가능 |
| 인프라 추가 | 벡터 DB 필요 | 추가 없음 |
| 정확도 | 근사값 | 정확한 SQL |
| 추가 패키지 | chromadb, sentence-transformers | 없음 |

→ "저번 패치 이후 반응" 같은 날짜 기반의 정확한 쿼리가 핵심이므로 **Tool Use** 채택.

**구현된 Tool 4종:**

| Tool | 설명 |
|------|------|
| `get_recent_reviews` | 기간·감성 필터로 리뷰 조회 |
| `get_patch_notes` | 패치노트·공지 조회 |
| `get_sentiment_stats` | 일별 감성 트렌드 |
| `search_by_keyword` | 키워드 검색 (코스튬, 밸런스 등) |

**Tool Use 흐름:**
1. 질문 입력
2. Claude가 필요한 Tool 선택 (0~N회 호출 가능)
3. `get_recent_reviews` / `get_patch_notes` / `get_sentiment_stats` / `search_by_keyword` 중 호출
4. 데이터 수집 완료 후 최종 답변 생성

**구현 완료 내역:**

| 파일 | 역할 |
|------|------|
| `scripts/qa_pipeline.py` | POC 스크립트 (데모 3문항 자동 + `--interactive` 대화형) |
| `backend/analyzer/game_qa.py` | Agent E 핵심 로직 |
| `backend/schemas/qa.py` | 요청/응답 Pydantic 스키마 |
| `backend/api/qa.py` | `POST /api/qa` 엔드포인트 |

**실행 방법:**
```bash
# 데모 모드 (예시 질문 3개 자동 실행)
python scripts/qa_pipeline.py --game "Elden Ring"

# 대화형 모드
python scripts/qa_pipeline.py --game "Elden Ring" --interactive

# 수집 기간 확장
python scripts/qa_pipeline.py --game "Elden Ring" --days 14 --interactive
```

---

## 2026-04-24 — Agent E: Live Ops Advisor 추가 (PR #4)

**배경:** 기존 에이전트들(A~D)은 모두 Push 방식(이상 감지 → 자동 알림). 운영자가 "최근 CS2 유저들이 왜 환불 요청을 많이 하지?"처럼 **능동적으로 질문**하면 DB에서 데이터를 꺼내 답변하는 On-demand 에이전트가 필요했다.

**RAG vs Tool Use 결정:**
- 구조화된 DB 데이터에는 정확한 SQL 쿼리가 벡터 검색보다 우수
- 추가 인프라(벡터 DB) 없이 구현 가능 → **Tool Use 선택**

**구현된 Tool 4종:**

| Tool | 설명 |
|------|------|
| `get_recent_reviews` | 최근 리뷰 N건 조회 |
| `get_patch_notes` | 최근 패치노트/공식 뉴스 조회 |
| `get_sentiment_stats` | 기간별 감성 통계 조회 |
| `search_by_keyword` | 키워드로 포스트 검색 |

**에이전트 루프:** Claude가 필요한 Tool을 선택·실행하며 최종 답변 생성 (agentic loop)

**주요 변경:**
- 질문 언어 감지: "질문과 동일한 언어로 답변" (한국어 질문 → 한국어, 영어 질문 → 영어)
- `--save` 옵션: 세션 종료 시 Q&A 결과를 `reports/qa-{게임슬러그}-{날짜}.md`로 저장
- 파일명 리팩터링: `game_qa.py` → `live_ops_advisor.py`, API 경로 `POST /api/qa` → `POST /api/live-ops-advisor`

---

## 2026-05-07 — Game Ops Portal 프론트엔드 (현재 브랜치: feature/portal)

**배경:** 기존 `GameDetail` 페이지는 단순 리포트 조회 화면이었다. Agent E(Live Ops Advisor)가 추가되면서 채팅 UI와 리포트를 한 화면에서 통합 제공하는 **운영자 포털**로 개편이 필요해졌다.

**구현 내용:**

| 탭 | 내용 |
|----|------|
| 탭 1 — 리포트 | 오늘의 리포트 + 감성 추이 차트 + 경쟁작 비교를 한 화면에 통합 |
| 탭 2 — AI 어드바이저 | Live Ops Advisor API 연동 채팅 UI, 추천 질문, 툴 사용 배지 표시 |

**변경된 파일:**

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/api.js` | `askLiveOpsAdvisor(gameId, question)` 함수 추가 |
| `frontend/src/components/AdvisorChat.jsx` | AI 어드바이저 채팅 컴포넌트 신규 생성 |
| `frontend/src/pages/GameDetail.jsx` | 탭 구조로 전면 개편 |

**`/game/:id` 페이지 구조:**

사이드바 + 탭 선택 영역으로 구성.

- **사이드바:** 게임 정보, 탭 선택 (리포트 / AI 어드바이저)
- **탭 1 — 리포트:**
  - 오늘의 리포트 (감성 바, 이슈, 키워드)
  - 최근 7일 감성 추이 차트
  - 경쟁작 비교 (현재 게임 자동 포함, 최대 3개 선택)
- **탭 2 — AI 어드바이저:**
  - 빈 상태일 때: 추천 질문 4개 버튼 표시
  - 채팅 UI: 유저/AI 말풍선, 사용 툴 배지 표시
  - 입력 기능: Enter로 전송, Shift+Enter로 줄바꿈

---

## 2026-06-23 — 멀티 플랫폼 데이터 소스 확장 (feature/multi-platform-sources)

**배경:** 기존 서비스는 Steam PC 게임만 커버했다. 모바일/크로스플랫폼 게임까지 수집 범위를 확장하기 위해 두 번째 플랫폼 소스를 추가했다.

**플랫폼 소스 선정 과정:**

초기 후보로 네이버 게임 라운지를 검토했으나 아래 이유로 Reddit으로 결정:

| 항목 | 네이버 게임 라운지 | Reddit (선택) |
|------|-----------------|--------------|
| API | 비공식 내부 API (구조 변경 리스크) | 공식 OAuth2 API |
| 커버리지 | 한국어 게임 한정 | 글로벌 전 장르 |
| 인증 | 불필요 | Client ID/Secret (무료 등록) |
| 데이터 품질 | 커뮤니티 글 | score(추천수) + comment_count 제공 |
| 안정성 | 낮음 (Playwright 교체 전례 있음) | 높음 |

→ 공식 API, 글로벌 커버리지, 모바일 게임 서브레딧 활성화 수준을 고려해 **Reddit** 채택.

**설계 결정 — 플러그인 크롤러 아키텍처:**

| 항목 | 기존 | 변경 후 |
|------|------|---------|
| 지원 플랫폼 | Steam (PC) 단일 | Steam + Reddit (모바일/크로스플랫폼) |
| 크롤러 구조 | 단일 모듈 함수 | `BaseCrawler` 추상 클래스 기반 플러그인 |
| Game 식별자 | `app_id` 단독 unique | `(platform, app_id)` 복합 unique |
| Post 출처 | 암묵적 (Steam 전용) | `source` 필드 명시 |
| LLM 프롬프트 | "Steam 커뮤니티" 고정 | 플랫폼별 레이블 동적 치환 |

**변경된 파일:**

| 파일 | 변경 내용 |
|------|----------|
| `backend/models/game.py` | `platform` 필드 추가, unique 제약 `app_id` → `(platform, app_id)` |
| `backend/models/post.py` | `source` 필드 추가, `post_id` 길이 100 → 150 |
| `backend/database.py` | SEED_GAMES에 `platform` 키 추가, Reddit 모바일 게임 5종 시드 추가, `init_db` upsert 로직 개선 |
| `backend/crawler/base_crawler.py` *(신규)* | `BaseCrawler` 추상 클래스 — 공통 DB 저장 로직 포함 |
| `backend/crawler/reddit_community.py` *(신규)* | Reddit OAuth2 기반 서브레딧 크롤러, flair로 news 분류 |
| `backend/crawler/steam_community.py` | `SteamCommunityCrawler` 클래스로 리팩토링, `source="steam"` 추가 |
| `backend/analyzer/llm_analyzer.py` | 프롬프트 멀티 플랫폼 인식, `_PLATFORM_LABELS` 맵 추가 |
| `backend/scheduler/jobs.py` | `_crawlers` 리스트로 플랫폼별 크롤러 순회 실행 |
| `backend/schemas/game.py` | `platform` 필드 API 응답에 노출 |
| `backend/config.py` | `reddit_client_id`, `reddit_client_secret` 설정 추가 |
| `.env.example` | Reddit OAuth2 자격증명 항목 추가 |

**신규 추가된 Reddit 게임 시드:**

| 게임명 | subreddit | 장르 |
|--------|-----------|------|
| Genshin Impact | r/Genshin_Impact | 모바일/PC RPG |
| Lost Ark | r/lostarkgame | PC MMORPG |
| PUBG Mobile | r/PUBGMobile | 모바일 배틀로얄 |
| Clash of Clans | r/ClashOfClans | 모바일 전략 |
| Clash Royale | r/ClashRoyale | 모바일 카드 |

**Reddit 크롤러 동작 방식:**
- OAuth2 `client_credentials` 방식으로 토큰 발급 (1시간 유효)
- `r/{subreddit}/new?limit=100` 으로 최신 글 수집
- flair에 patch/update/announcement 등 포함 → `post_type="news"`, 나머지 → `"community"`
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` 미설정 시 경고 로그 후 조용히 건너뜀

**확장 구조 — 새 플랫폼 추가 방법:**
1. `crawler/base_crawler.py`의 `BaseCrawler`를 상속한 크롤러 작성
2. `database.py`의 `SEED_GAMES`에 `{"platform": "new_platform", ...}` 항목 추가
3. `analyzer/llm_analyzer.py`의 `_PLATFORM_LABELS`에 레이블 등록
4. `scheduler/jobs.py`의 `_crawlers` 리스트에 인스턴스 추가

---

## 2026-06-28 — Reddit 데이터 수집 테스트 및 포털 통합 (feature/multi-platform)

**배경:** 멀티 플랫폼 크롤러는 스케줄러에 연결되어 있었으나, 수동 `trigger-crawl` 엔드포인트가 Steam 크롤러만 호출했고, 프론트엔드에서는 게시글의 출처(source)를 구분하거나 게임의 플랫폼 정보를 표시할 수 없었다.

**변경 내용:**

| 파일 | 변경 내용 |
|------|----------|
| `backend/main.py` | `trigger-crawl`이 Steam 함수만 호출하던 것을 `SteamCommunityCrawler` + `RedditCommunityCrawler` 순차 실행으로 변경 |
| `backend/api/posts.py` *(신규)* | `GET /api/posts/{game_id}` — `source`, `days_back`, `limit` 파라미터로 수집 게시글 조회, 인기순(좋아요+댓글) 정렬 |
| `backend/schemas/report.py` | `DashboardSummaryItem`에 `platform` 필드 추가 |
| `backend/api/dashboard.py` | 대시보드 응답에 `game.platform` 포함 |
| `frontend/src/api.js` | `getPosts(gameId, { source, daysBack, limit })` 함수 추가 |
| `frontend/src/components/ReportCard.jsx` | 플랫폼 뱃지 추가 (파란색 = Steam, 주황색 = Reddit) |
| `frontend/src/pages/Dashboard.jsx` | 대시보드 API의 `platform`을 `ReportCard`에 전달 |
| `frontend/src/pages/GameDetail.jsx` | "최근 게시글" 탭 신규 추가 — 플랫폼 필터, 기간 선택, 게시글별 뱃지 표시 |

**신규 API 엔드포인트:**

```
GET /api/posts/{game_id}?source=reddit&days_back=1&limit=50
```

- `source`: `steam` 또는 `reddit` (생략 시 전체)
- `days_back`: 1~30 (기본 1)
- `limit`: 1~200 (기본 50)
- 응답: `like_count + comment_count` 합산 내림차순 정렬

**포털 "최근 게시글" 탭 (`/game/:id`):**

- 플랫폼 필터 드롭다운 (전체 / Steam / Reddit)
- 수집 기간 선택 (1 / 3 / 7일)
- 게시글마다 출처 뱃지, 유형 뱃지(리뷰/공지/커뮤니티), 제목, 내용 미리보기, 좋아요·댓글·작성자·날짜 표시

---

## 2026-07-02 — 모바일 게임 Top 10 확정 및 Google Play · App Store 크롤러 추가 (feature/multi-platform)

**배경:** Reddit 크롤러만으로는 커뮤니티 토론만 수집할 수 있었다. 실제 설치자 기반의 평점·리뷰가 필요해 Steam과 동일한 성격의 모바일 플랫폼 리뷰 소스(Google Play, App Store)를 추가했다. 세 소스를 하나의 게임 엔티티로 묶어 통합 분석 및 단일 리포트를 제공한다.

**모바일 게임 Top 10 확정:**

기존 5개(임의 선정, Lost Ark 포함) → Reddit 커뮤니티 활성도 + 글로벌 MAU 기준 재선정:

| 게임 | Google Play 패키지명 | App Store ID | subreddit |
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

**설계 변경 — 게임 엔티티 구조:**

| 항목 | 기존 | 변경 후 |
|------|------|---------|
| 모바일 게임 platform 값 | `"reddit"` | `"mobile"` |
| 소스 식별자 | `app_id` 하나로 통합 | `reddit_id` · `play_store_id` · `app_store_id` 분리 |
| 수집 소스 수 | 1개 (Reddit) | 3개 (Reddit + Google Play + App Store) |
| 리포트 | 소스별 분리 가능성 | 하나의 game_id로 통합 → 단일 리포트 |

**신규/변경된 파일:**

| 파일 | 변경 내용 |
|------|----------|
| `backend/models/game.py` | `reddit_id`, `play_store_id`, `app_store_id` 필드 추가 |
| `backend/models/post.py` | `rating: Float` 필드 추가, `like_count` / `comment_count` nullable로 변경 |
| `backend/database.py` | SEED_GAMES 모바일 10개 → platform="mobile", 3개 스토어 ID 포함 |
| `backend/crawler/base_crawler.py` | `_games_query()` 오버라이드 포인트 추가 |
| `backend/crawler/reddit_community.py` | `platform="mobile"` + `game.reddit_id` 사용으로 변경 |
| `backend/crawler/google_play.py` *(신규)* | `google-play-scraper` 기반, rating + thumbsUpCount 수집 |
| `backend/crawler/app_store.py` *(신규)* | iTunes RSS 기반, rating 수집 (like_count=null) |
| `backend/scheduler/jobs.py` | `GooglePlayCrawler`, `AppStoreCrawler` 추가 |
| `backend/main.py` | trigger-crawl에 새 크롤러 등록 |
| `backend/requirements.txt` | `google-play-scraper==1.2.7` 추가 |
| `backend/analyzer/llm_analyzer.py` | 포스트 출력에 ★ 평점 표시, 플랫폼 레이블 "mobile"로 통합 |

**소스별 수집 데이터:**

| 소스 | rating | like_count | comment_count |
|------|--------|------------|---------------|
| Steam | null | helpful 수 | null |
| Reddit | null | upvote score | 댓글 수 |
| Google Play | 1.0~5.0 ✅ | thumbsUpCount ✅ | null |
| App Store | 1.0~5.0 ✅ | null | null |

**배포 후 버그 픽스:**

실제 수집·분석 실행 중 발견된 문제들을 수정했다.

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `backend/schemas/post.py` | `like_count`/`comment_count`가 `int`(non-null)로 선언 → 500 에러 | `int \| None`으로 변경, `rating`·`source` 필드 추가 |
| `backend/api/posts.py` | 동일한 nullable 문제 + NULL 포함 컬럼 정렬 오류 | `int \| None` 수정, `COALESCE` 기반 정렬로 변경 |
| `backend/analyzer/llm_analyzer.py` | `rollback()` 후 `game.name` 접근 시 SQLAlchemy greenlet 에러 | 루프 시작 시 `game_name = game.name` 선캡처 |
| `backend/analyzer/llm_analyzer.py` | `like_count + comment_count` 정렬 시 NULL 덧셈 TypeError | `(p.like_count or 0) + (p.comment_count or 0)` 처리 |
| `backend/analyzer/llm_analyzer.py` | Claude 모델 ID `claude-sonnet-4-20250514` → 404 오류 | `claude-sonnet-4-6`으로 수정 |
| `backend/analyzer/action_recommender.py` | 동일한 모델 ID 문제 | `claude-sonnet-4-6`으로 수정 |
| `.claude/settings.local.json` | curl 허용 명령이 엔드포인트별 개별 항목 13개 | `curl -s "http://localhost:8000/api/*` 등 와일드카드 3줄로 통합 |

---

## 2026-07-03 — 포탈 플랫폼 필터 추가 (Steam / 모바일 분리)

**배경:** 모바일 게임 10종이 추가되면서 대시보드에 Steam PC 게임과 모바일 게임이 혼재하게 됐다. 서로 다른 플랫폼을 같은 화면에서 비교하거나 분석하는 것은 의미가 없으므로, 포탈 전체에서 플랫폼별 분리 필터를 제공하기로 했다.

**변경 내용:**

| 페이지 | 변경 내용 |
|--------|----------|
| `Dashboard` | 상단에 전체 / PC(Steam) / 모바일 필터 버튼 추가; 각 버튼에 해당 게임 수 표시 |
| `Alerts` | 플랫폼 필터를 상위 개념으로 별도 행에 배치; 심각도 탭·게임 드롭다운은 하위 행에 들여쓰기 + 좌측 세로선으로 계층 표현 |
| `Compare` | 플랫폼 필터 추가; 플랫폼 변경 시 선택된 게임 및 비교 결과 초기화 |
| `ReportCard` | 플랫폼 뱃지 제거 (상단 필터로 대체되어 불필요) |

**이슈 탭 필터 계층 구조 설계:**

단순히 행을 분리하는 것만으로는 상하위 관계가 직관적으로 느껴지지 않아, 레이블 + 들여쓰기 + 좌측 세로선(`border-l-2`) 방식으로 시각적 계층을 표현했다.

```
플랫폼                          ← 상위 레이블
  [ 전체 ]  [ PC (Steam) ]  [ 모바일 ]

│  필터                         ← 하위 레이블 (들여쓰기 + 좌측 세로선)
│  [ 전체 / 🚨CRITICAL / ⚠️WARNING / 미확인 ]   [ 게임 선택 ▾ ]
```

**추가 개선:**
- `getGames()` 실패 시 에러 상태(`gamesError`)를 노출해 조용한 실패 방지
- 게임 드롭다운 `value`를 `String(g.id)`로 통일 (`gameFilter` 문자열 타입과 일치)

---

## 2026-07-05 — 프론트엔드 UI 전면 개편 (프로덕션 수준 업그레이드)

**배경:** 기존 포탈은 Tailwind CSS 기반의 기능 중심 레이아웃으로, 데모 수준의 완성도였다. 서비스 출시를 목표로 Linear·Vercel·Supabase 급의 프로덕션 품질로 전면 재설계했다.

**핵심 변경 사항:**

| 영역 | 기존 | 변경 후 |
|------|------|---------|
| 레이아웃 | 상단 텍스트 내비게이션 | 다크 사이드바 (240px, 데스크탑) + 아이콘 탑바 (모바일) |
| 폰트 | 시스템 기본 | Inter (Google Fonts) |
| 아이콘 | 이모지 | lucide-react (일관된 SVG 아이콘 라이브러리) |
| 알림 | 브라우저 `alert()` | Toast 컴포넌트 (`useToast` 훅, 슬라이드인 애니메이션) |
| 감성 색상 | 탁한 세이지 그린·테라코타 | 선명한 green-500 · slate-400 · red-500 |

**페이지별 주요 개선:**

*대시보드:*
- 모니터링 게임 수 · 수집 데이터 · 활성 이슈를 보여주는 3-stat 요약 카드 행 추가
- 플랫폼 탭에 아이콘(Monitor / Smartphone / Layers) 추가, 세그먼트 스위처 디자인으로 변경
- `ReportCard`: `rounded-2xl`, 플랫폼 배지, 심각도 라벨 배지, 감성 분포 도트 칩

*이슈 트래킹:*
- 필터 영역을 `rounded-2xl` 카드로 통합
- `AlertCard`: 심각도별 배경 틴트, lucide 아이콘 배지, Alert 유형 행 추가
- `AlertDetail`: 심각도 그라디언트 헤더, 슬라이드인 패널 애니메이션, 아이콘 부서 탭, Loader2 스피너

*게임 상세:*
- 사이드바 탭에 아이콘 및 플랫폼 배지 추가
- `AdvisorChat`: 채팅 버블 리디자인, Bot 아바타, 메시지 타임스탬프
- `TrendChart`: 커스텀 툴팁, 클린 축 스타일링

**신규 파일:**

| 파일 | 역할 |
|------|------|
| `frontend/src/components/Toast.jsx` | `ToastProvider` + `useToast` 훅 — 전역 토스트 알림 시스템 |
| `frontend/src/components/index.js` | 컴포넌트 배럴 익스포트 |

---

## 현재 상태 및 미결 사항

| 항목 | 상태 |
|------|------|
| Steam 데이터 수집 파이프라인 | 완료 |
| 이상 감지 + Slack 알림 | 완료 |
| 커스텀 게임 모드 (POC) | 완료 |
| Live Ops Advisor (Tool Use) | 완료 |
| Game Ops Portal 프론트엔드 | 완료 (feature/portal 머지) |
| 멀티 플랫폼 소스 확장 | 완료 (feature/multi-platform) |
| Reddit 포털 통합 (게시글 탭 + 플랫폼 뱃지) | 완료 |
| 모바일 Top 10 확정 + Google Play / App Store 크롤러 | 완료 |
| 프론트엔드 UI 전면 개편 (프로덕션 수준) | 완료 |
| Reddit API 키 발급 및 수집 | 미완료 (API 정책 페이지 진입 불가 이슈) |
