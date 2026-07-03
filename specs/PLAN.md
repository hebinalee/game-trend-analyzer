# Project Plan — AS-IS → TO-BE 고도화

## 목표

Steam 커뮤니티 리포트 생성 도구(수동)를  
이상 감지 → 원인 분석 → 대응 제안 → 알림까지 자동화하는  
**능동적 AI 업무 비서**로 전환한다.

---

## 마일스톤

| # | 마일스톤 | 내용 | 상태 |
|---|---------|------|------|
| M1 | 이상 감지 파이프라인 | Agent A + C + DB 모델 | **완료** |
| M2 | 알림 연동 | Agent B (Slack) | **완료** |
| M3 | 이슈 관리 UI | Agent D (API + Frontend) | **완료** |
| M4 | 통합 검증 | 통합 포인트 검증, 버그 수정 | **완료** |
| M5 | 멀티 플랫폼 지원 | Reddit·Google Play·App Store 크롤러 추가, 포탈 플랫폼 필터 | **완료** |

---

## 의존성

```
M1 (A+C) ──▶ M2 (B)   # 알림은 Alert가 있어야 의미있음
M1 (A+C) ──▶ M3 (D)   # UI는 Alert API가 있어야 구현 가능
M2, M3   ──▶ M4        # 통합 검증은 전체 완료 후
```

M2와 M3는 M1 완료 후 **병렬 진행 가능**.

---

## 스프린트 계획

### Sprint 1 (완료)
- [x] Alert 모델 설계 및 DB 마이그레이션 (`models/alert.py`)
- [x] 이상 감지 엔진 구현 (`detector/anomaly_detector.py`)
- [x] 대응 제안 엔진 구현 (`analyzer/action_recommender.py`)
- [x] 스케줄러 연동 (크롤링 완료 → 감지 자동 실행)
- [x] 수동 트리거 API (`POST /api/admin/trigger-detect`)
- [x] 팀 문서화 (`docs/`)

### Sprint 2 (완료)
- [x] Agent B: Slack notifier 구현
- [x] Agent D: 이슈 관리 API 3종 구현
- [x] Agent D: 프론트엔드 이슈 트래킹 UI

### Sprint 3 (완료)
- [x] Agent E: LiveOps Advisor (Tool Use 에이전트)
- [x] E2E 통합 검증 및 배포 후 버그 수정
- [x] README 업데이트 (EN/KO)

### Sprint 4 (완료)
- [x] Reddit 커뮤니티 크롤러 (PC + 모바일 공용)
- [x] Google Play 리뷰 크롤러
- [x] App Store 리뷰 크롤러
- [x] Game 모델 멀티 플랫폼 확장 (platform, reddit_id, play_store_id, app_store_id)
- [x] Post 모델 source·rating 필드 추가
- [x] 모바일 게임 10종 seed 데이터 추가
- [x] 포탈 전체(대시보드·이슈·비교) 플랫폼 필터(Steam/모바일) 추가

---

## 현재 상태 (2026-07-01 기준)

완료된 작업 (전체):
- M1–M5 모든 마일스톤 완료
- 20개 게임 (Steam 10 + 모바일 10) 운영 중
- 멀티 플랫폼 크롤러 4종 (Steam, Reddit, Google Play, App Store)
- 이상 감지 → 대응 제안 → Slack 알림 파이프라인 가동
- LiveOps Advisor (on-demand 자연어 질의)
- 포탈 플랫폼 필터 (Steam/모바일 분리)

다음 후보 작업:
- 감지 임계값 튜닝 (운영 데이터 2주 이상 확보 후)
- 오탐율 리뷰 (CRITICAL 알림 < 20% 기준)
- 단위 테스트 추가 (Agent A 우선)

---

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Steam API 크롤링 실패 | 감지 데이터 공백 | 기존 예외처리 유지, 알림 발송 시 데이터 부족 명시 |
| Claude API 지연/오류 | 대응 제안 누락 | recommendations 실패 시 Alert는 보존, 재시도는 수동 트리거로 |
| Slack webhook 오류 | 알림 누락 | DB에 Alert 저장 후 발송 시도 → 실패 시 `notified=False` 플래그 유지 |
| 오탐 알림 남발 | 팀 신뢰 저하 | 쿨다운 6h + 최소 데이터 기준 + 임계값 보수적 설정 |
