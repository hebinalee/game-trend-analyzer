# Architecture — Game Trend AI

## AS-IS (수동 비서)

```
Steam API ──▶ Crawler ──▶ PostgreSQL ──▶ LLM Analyzer ──▶ Report
                                                              │
                                                         React Dashboard
                                                         (사람이 직접 확인)
```

- 스케줄: 크롤링 6h 주기, 분석 매일 07:00 KST
- 출력: 게임별 일간 리포트 (summary, hot_topics, sentiment, key_issues)
- 한계: 이상 징후를 감지·통보하는 기능 없음. 운영 담당자가 대시보드를 주기적으로 열어봐야 함

---

## TO-BE (능동 비서)

```
Steam API ──▶ Crawler ──▶ PostgreSQL
                               │
                    ┌──────────▼──────────┐
                    │   Agent A           │  이상 감지
                    │   anomaly_detector  │  sentiment_drop / volume_spike / keyword_alert
                    └──────────┬──────────┘
                               │ Alert 생성
                    ┌──────────▼──────────┐
                    │   Agent C           │  대응 제안
                    │   action_recommender│  Claude API → 부서별 액션 아이템
                    └──────────┬──────────┘
                               │ recommendations 채움
                    ┌──────────▼──────────┐
                    │   Agent B           │  Slack 알림
                    │   slack_notifier    │  CRITICAL/WARNING → 담당자 채널
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Agent D           │  이슈 관리 UI
                    │   API + Frontend    │  이슈 목록, 상태 변경, 대응 방안 열람
                    └─────────────────────┘
```

---

## 트리거 체인

| 단계 | 트리거 | 담당 |
|------|--------|------|
| 크롤링 | APScheduler 6h 주기 + 앱 시작 1분 후 | `scheduler/jobs.py` |
| 이상 감지 | 크롤링 완료 직후 자동 | Agent A |
| 대응 제안 | Alert flush 직후 (같은 트랜잭션) | Agent C |
| Slack 알림 | Alert commit 직후 (별도 비동기) | Agent B |
| LLM 분석 | 매일 07:00 KST (별도 스케줄) | 기존 analyzer |

---

## 데이터 계약

### Alert (alerts 테이블)

```json
{
  "id": 1,
  "game_id": 1,
  "severity": "CRITICAL | WARNING | INFO",
  "alert_type": "sentiment_drop | volume_spike | keyword_alert",
  "title": "사람이 읽을 수 있는 한 줄 요약",
  "detail": {
    // alert_type별 수치 데이터 (아래 참고)
  },
  "recommendations": {
    "summary": "이슈 원인 추정 및 핵심 대응 방향",
    "cs":        ["...", "...", "..."],
    "planning":  ["...", "...", "..."],
    "marketing": ["...", "...", "..."],
    "business":  ["...", "...", "..."]
  },
  "status": "new | acknowledged | resolved",
  "detected_at": "2026-04-15T10:00:00Z"
}
```

### detail 스키마 (alert_type별)

**sentiment_drop**
```json
{
  "baseline_negative_ratio": 0.41,
  "current_negative_ratio": 0.72,
  "diff": 0.31,
  "current_reviews": 45,
  "baseline_reviews": 120,
  "window_hours": 6
}
```

**volume_spike**
```json
{
  "baseline_hourly_rate": 3.2,
  "current_hourly_rate": 18.5,
  "ratio": 5.78,
  "current_review_count": 111,
  "window_hours": 6
}
```

**keyword_alert**
```json
{
  "matched_keywords": ["환불", "서버 다운"],
  "keyword_ratio": 0.13,
  "total_posts": 87,
  "window_hours": 6
}
```

---

## 감지 임계값 (Agent A)

| 타입 | WARNING | CRITICAL |
|------|---------|---------|
| sentiment_drop | 부정 비율 +20%p↑ & 현재 ≥50% | +30%p↑ & 현재 ≥60% |
| volume_spike | 시간당 리뷰 3배↑ (최소 10건) | 5배↑ (최소 10건) |
| keyword_alert (긴급) | — | 긴급 키워드 ≥10% 포스트 |
| keyword_alert (경고) | 경고 키워드 ≥15% 포스트 | — |

- 동일 게임·타입 중복 알림 억제: 6시간 쿨다운
- 최소 데이터 기준 미충족 시 스킵

---

## 주요 파일 맵

```
backend/
├── detector/
│   ├── __init__.py
│   └── anomaly_detector.py     # Agent A: 감지 로직, detect_all_games()
├── analyzer/
│   ├── llm_analyzer.py         # 기존: 일간 리포트 생성
│   └── action_recommender.py   # Agent C: 대응 제안, fill_recommendations()
├── notifier/
│   ├── __init__.py             # Agent B: 예정
│   └── slack_notifier.py       # Agent B: 예정
├── models/
│   ├── game.py
│   ├── post.py
│   ├── report.py
│   └── alert.py                # 신규: alerts 테이블
├── api/
│   ├── games.py
│   ├── reports.py
│   ├── dashboard.py
│   └── alerts.py               # Agent D: 예정
└── scheduler/
    └── jobs.py                 # 크롤링 → 감지 체인 연결됨
```
