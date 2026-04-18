# Agent A — 이상 감지 엔진

**상태**: 완료  
**담당 파일**: `backend/detector/anomaly_detector.py`

---

## Role

크롤링 완료 후 자동 실행되어, 게임별 커뮤니티 데이터에서  
비정상적인 패턴을 탐지하고 `Alert` 레코드를 생성한다.

---

## 입력 계약

| 소스 | 내용 |
|------|------|
| `posts` 테이블 | 현재 윈도우(최근 6h) + 베이스라인 윈도우(직전 18h) 포스트 |
| `games` 테이블 | 활성 게임 목록 (`is_active=True`) |

---

## 출력 계약

| 대상 | 내용 |
|------|------|
| `alerts` 테이블 | 감지된 이상별 Alert 레코드 (flush 후 Agent C가 채움) |
| 반환값 | `list[Alert]` (감지된 Alert 전체) |

---

## 감지 유형 및 임계값

### sentiment_drop (부정 리뷰 비율 급증)
- 기준: 현재 6h vs 직전 18h 리뷰의 Not Recommended 비율 차이
- WARNING: diff ≥ +20%p AND 현재 비율 ≥ 50%
- CRITICAL: diff ≥ +30%p AND 현재 비율 ≥ 60%
- 최소 데이터: 현재 윈도우 리뷰 5건 이상

### volume_spike (리뷰 볼륨 급증)
- 기준: 시간당 리뷰 수 비율 (현재 / 베이스라인)
- WARNING: ≥ 3배 AND 현재 리뷰 수 ≥ 10건
- CRITICAL: ≥ 5배 AND 현재 리뷰 수 ≥ 10건

### keyword_alert (긴급 키워드 감지)
- 긴급 키워드(환불, 서버 다운, 핵 등): 포스트의 10% 이상 → CRITICAL
- 경고 키워드(버그, 렉, crash 등): 포스트의 15% 이상 → WARNING

---

## 주요 설계 결정

- **쿨다운 6h**: 동일 게임·타입 중복 Alert 억제. 장시간 이슈 지속 시 재알림 방지 목적.
- **베이스라인 18h**: 크롤링 주기(6h)의 3배. 베이스라인이 너무 짧으면 일시적 패턴에 흔들림.
- **flush 후 commit 없음**: Agent C가 recommendations를 채운 뒤 한 번에 commit.
- **예외 격리**: 게임별 try/except. 한 게임 실패가 나머지를 막지 않음.

---

## 체크리스트

- [x] Alert 모델 정의 (`models/alert.py`)
- [x] 감지 로직 3종 구현
- [x] 중복 억제 (쿨다운 체크)
- [x] Agent C 연동 (`fill_recommendations` 호출)
- [x] 스케줄러 연동 (`jobs.py` 크롤링 후 자동 실행)
- [x] 수동 트리거 API (`POST /api/admin/trigger-detect`)
- [ ] 단위 테스트 (M4에서 진행)
- [ ] 임계값 튜닝 (운영 데이터 확보 후)
