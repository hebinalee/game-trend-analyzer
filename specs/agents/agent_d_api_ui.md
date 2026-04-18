# Agent D — API & 프론트엔드

**상태**: 완료  
**담당 파일**: `backend/api/alerts.py`, `frontend/src/`

---

## Role

운영 담당자가 감지된 이슈를 확인하고 대응 방안을 열람하며  
이슈 상태(new → acknowledged → resolved)를 관리할 수 있는  
API와 React UI를 구현한다.

---

## API 계약

### GET /api/alerts
이슈 목록 조회

**Query params**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `game_id` | int | — | 특정 게임 필터 |
| `severity` | str | — | CRITICAL / WARNING / INFO |
| `status` | str | — | new / acknowledged / resolved |
| `limit` | int | 50 | 최대 반환 수 |

**Response**
```json
[
  {
    "id": 1,
    "game_id": 1,
    "game_name": "Counter-Strike 2",
    "severity": "CRITICAL",
    "alert_type": "sentiment_drop",
    "title": "[CS2] 부정 리뷰 비율 급증 (41% → 72%, +31%p)",
    "status": "new",
    "detected_at": "2026-04-15T10:00:00Z",
    "notified": true
  }
]
```

### GET /api/alerts/{alert_id}
이슈 상세 조회 (detail + recommendations 포함)

**Response**: Alert 전체 필드

### PATCH /api/alerts/{alert_id}/status
이슈 상태 변경

**Request body**
```json
{ "status": "acknowledged" }
```

**허용 전환**: `new → acknowledged`, `acknowledged → resolved`  
역방향 전환 불가 (400 반환).

---

## 프론트엔드 설계

### 신규 페이지: `/alerts`

**이슈 목록 페이지**
- 필터 탭: All / CRITICAL / WARNING / 미확인(new)
- 게임별 필터 드롭다운
- 카드 목록: severity 배지(색상), 게임명, 이슈 요약, 감지 시간, 상태
- CRITICAL은 빨간 배경 강조

**이슈 상세 모달 또는 슬라이드 패널**
- 감지 상세 데이터 (detail 필드 시각화)
- 부서별 대응 방안 탭 (CS / 기획 / 마케팅 / 사업)
- 상태 변경 버튼 (acknowledged → resolved)

### 기존 대시보드 변경

- 헤더에 미확인 CRITICAL 이슈 수 배지 추가
- 게임 카드에 최신 Alert severity 인디케이터 추가 (빨간/노란 점)

---

## 구현 가이드라인

**Backend**
1. 기존 `api/reports.py` 패턴 그대로 적용 (Depends(get_db), router)
2. `schemas/alert.py` — AlertListItem, AlertDetail, AlertStatusUpdate Pydantic 스키마
3. 상태 전환 유효성은 API 레이어에서 검증

**Frontend**
1. 기존 `src/api.js`에 alerts 관련 함수 추가
2. `src/pages/Alerts.jsx` — 이슈 목록
3. `src/components/AlertCard.jsx` — 카드 컴포넌트
4. `src/components/AlertDetail.jsx` — 상세 패널
5. `App.jsx`에 `/alerts` 라우트 추가

---

## 체크리스트

**Backend**
- [x] `backend/schemas/alert.py` — AlertListItem, AlertDetail, AlertStatusUpdate
- [x] `backend/api/alerts.py` — GET /api/alerts, GET /api/alerts/{id}, PATCH /api/alerts/{id}/status, GET /api/alerts/unread-count
- [x] `backend/main.py` — alerts router 등록

**Frontend**
- [x] `src/api.js` — `getAlerts()`, `getAlertDetail()`, `updateAlertStatus()`, `getAlertsUnreadCount()`
- [x] `src/pages/Alerts.jsx` — 이슈 목록 (심각도 탭 + 게임 필터 + 슬라이드 패널)
- [x] `src/components/AlertCard.jsx` — severity/status 배지, timeAgo
- [x] `src/components/AlertDetail.jsx` — 감지 수치 + 부서별 대응 방안 탭 + 상태 변경
- [x] `src/App.jsx` — `/alerts` 라우트 + 네비 링크 + CRITICAL 배지 (1분 폴링)
- [x] Dashboard 헤더 → App.jsx 네비에 통합
- [x] 게임 카드 severity 인디케이터 (빨간/노란 점)
