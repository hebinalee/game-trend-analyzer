# Agent C — 대응 제안 엔진

**상태**: 완료  
**담당 파일**: `backend/analyzer/action_recommender.py`

---

## Role

Alert 생성 직후 Claude API를 호출하여  
마케팅·CS·기획·사업 부서별 구체적인 대응 방안을 생성하고  
`Alert.recommendations` 필드를 채운다.

---

## 입력 계약

| 인수 | 타입 | 내용 |
|------|------|------|
| `alert` | `Alert` | flush된 Alert 객체 (id 있음, recommendations 비어있음) |
| `game` | `Game` | 게임 정보 (name 등) |
| `current_posts` | `list[Post]` | 현재 윈도우 포스트 (컨텍스트용) |

---

## 출력 계약

`Alert.recommendations` 필드를 아래 JSON 구조로 채운다.  
DB commit은 호출자(Agent A)가 담당한다.

```json
{
  "summary": "이슈 원인 추정 및 핵심 대응 방향 2~3줄",
  "cs":        ["액션 1", "액션 2", "액션 3"],
  "planning":  ["액션 1", "액션 2", "액션 3"],
  "marketing": ["액션 1", "액션 2", "액션 3"],
  "business":  ["액션 1", "액션 2", "액션 3"]
}
```

실패 시: `{"error": "오류 메시지"}` — Alert 자체는 보존됨.

---

## 프롬프트 설계

- **System**: 게임 운영 전문 컨설턴트 페르소나. 즉시 실행 가능한 액션 아이템 중심.
- **User**: 게임명 / 이슈 유형 / 심각도 / 감지 상세 데이터 / 관련 게시글 샘플(최대 10건)
- **모델**: `claude-sonnet-4-20250514`, max_tokens=1024

포스트 샘플은 인기순(like + comment) 상위 10개 리뷰만 포함.  
뉴스는 컨텍스트 노이즈가 많아 제외.

---

## 주요 설계 결정

- **같은 트랜잭션**: Alert flush 직후 동기 호출. 추천 없는 Alert가 commit되는 상황 최소화.
- **실패 허용**: API 오류 시 예외를 삼키고 `recommendations.error` 기록. 파이프라인 중단 없음.
- **부서별 3개 제한**: 너무 많으면 읽히지 않음. 구체적인 3개가 모호한 10개보다 낫다.

---

## 체크리스트

- [x] `fill_recommendations()` 구현
- [x] 부서별 프롬프트 설계
- [x] 포스트 샘플 포맷터 (`_format_posts_sample`)
- [x] JSON 파싱 + 코드블록 추출 처리
- [x] 실패 시 Alert 보존 처리
- [ ] 프롬프트 품질 검토 (실제 알림 발생 후 출력 검토)
- [ ] 부서 키 확장 가능성 검토 (e.g., `qa`, `community_manager`)
