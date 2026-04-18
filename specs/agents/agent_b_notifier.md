# Agent B — Slack 알림 엔진

**상태**: 완료  
**담당 파일**: `backend/notifier/slack_notifier.py`

---

## Role

Alert가 DB에 commit된 직후 Slack webhook으로 알림을 전송한다.  
CRITICAL은 즉시, WARNING은 요약하여 전송.  
전송 실패 시 `alerts.notified` 플래그를 `False`로 유지하여 재시도 가능하게 한다.

---

## 입력 계약

| 인수 | 타입 | 내용 |
|------|------|------|
| `alert` | `Alert` | commit된 Alert (recommendations 포함) |
| `game` | `Game` | 게임 정보 |

환경 변수:
- `SLACK_WEBHOOK_URL` — Slack Incoming Webhook URL
- `SLACK_CHANNEL` — 기본 채널 (선택, webhook에 이미 지정된 경우 생략)

---

## 출력 계약

- Slack 채널에 메시지 전송
- `Alert.notified = True` 업데이트 (성공 시)
- 실패 시 예외를 삼키고 로깅, Alert는 보존

---

## 알림 포맷 설계

### CRITICAL
```
🚨 *[CS2] CRITICAL 이슈 감지*
> 부정 리뷰 비율 급증 (41% → 72%, +31%p)

*감지 데이터*
• 현재 비율: 72% (리뷰 45건)
• 직전 비율: 41% (리뷰 120건)

*핵심 대응 방향*
서버 불안정으로 인한 부정 여론 급증 추정. 즉각적인 공지 및 CS 대응 필요.

*대응 방안 요약*
• CS: 공지 문구 초안 준비, 이슈 FAQ 업데이트
• 기획: 서버 안정화 패치 우선순위 상향
• 마케팅: SNS 커뮤니케이션 일시 보류
• 사업: 환불 요청 급증 모니터링 강화

🔗 대시보드에서 전체 보기 → http://localhost:3000/alerts/{alert_id}
```

### WARNING
```
⚠️ *[Rust] WARNING — 경고 키워드 급증*
> 버그, 렉, disconnect 키워드가 전체 포스트의 18%에서 감지됨

🔗 대시보드 → http://localhost:3000/alerts/{alert_id}
```

---

## 구현 가이드라인

1. `httpx.AsyncClient`로 webhook POST 요청 (기존 크롤러와 동일 패턴)
2. Slack Block Kit 사용 — 단순 text보다 구조화된 메시지 전달
3. `Alert` 모델에 `notified: bool = False` 컬럼 추가 필요
4. 재시도 로직: 스케줄러에 `retry_failed_notifications` 주기 작업 추가 (1h 주기)

---

## 필요한 모델 변경

`backend/models/alert.py`에 추가:
```python
notified: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

## 체크리스트

- [x] `Alert.notified` 컬럼 추가
- [x] `backend/notifier/__init__.py` 생성
- [x] `backend/notifier/slack_notifier.py` 구현
  - [x] `send_alert(alert, game, db)` 함수
  - [x] Block Kit 메시지 포맷터 (CRITICAL 상세 / WARNING 요약)
  - [x] 전송 성공 시 `notified=True` 업데이트
- [x] `anomaly_detector.py`의 `detect_all_games()`에서 commit 후 notifier 호출
- [x] `.env.example`에 `SLACK_WEBHOOK_URL`, `DASHBOARD_URL` 추가
- [x] `config.py`에 `slack_webhook_url`, `dashboard_url` 추가
- [x] 수동 트리거: `POST /api/admin/trigger-notify/{alert_id}`
- [x] 재시도 스케줄 job (`retry_notify_job`, 1h 주기)
