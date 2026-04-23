# Agent E — Game Ops QA

**상태**: 완료  
**담당 파일**: `backend/analyzer/game_qa.py`, `backend/api/qa.py`, `backend/schemas/qa.py`  
**POC**: `scripts/qa_pipeline.py`

---

## Role

운영 담당자가 자연어 질문을 입력하면, Claude Tool Use 기반의 에이전트가  
필요한 데이터를 스스로 조회하고 근거 있는 답변을 생성한다.

RAG 대신 Tool Use를 선택한 이유:
- 구조화된 DB 데이터에는 정확한 쿼리가 벡터 유사도 검색보다 우수
- 날짜 필터링·감성 집계는 근사값이 아닌 정확한 값이 필요
- 추가 인프라(벡터 DB) 없이 구현 가능

---

## 입력 계약

| 소스 | 내용 |
|------|------|
| `POST /api/qa` body | `game_id: int`, `question: str` |
| `posts` 테이블 | 리뷰(`post_type="review"`) + 뉴스(`post_type="news"`) |

---

## 출력 계약

```json
{
  "answer": "데이터 기반 분석 답변 (질문 언어와 동일)",
  "tools_used": ["get_recent_reviews", "search_by_keyword"],
  "game_name": "Counter-Strike 2"
}
```

---

## Tool 목록

| Tool | 설명 | 주요 파라미터 |
|------|------|--------------|
| `get_recent_reviews` | 최근 N일 리뷰 + 감성 비율 | `days_back`, `sentiment`, `limit` |
| `get_patch_notes` | 최근 N일 패치노트·공지 | `days_back` |
| `get_sentiment_stats` | 일별 감성 트렌드 | `days_back` |
| `search_by_keyword` | 키워드 포함 리뷰 검색 | `keywords`, `days_back` |

---

## 에이전트 루프

```
사용자 질문
    └─▶ Claude (claude-sonnet-4-6)
          ├─ tool_use → Tool 실행 (DB 조회) → 결과 반환 → 반복
          └─ end_turn → 최종 답변 생성
```

- 최대 반복 없음 (Claude가 충분한 데이터를 모으면 스스로 종료)
- 동일 Tool을 파라미터를 달리해 복수 호출 가능
- 답변은 질문과 동일한 언어로 생성

---

## API 계약

### POST /api/qa

**Request**
```json
{ "game_id": 1, "question": "최근 부정 리뷰 원인이 뭐야?" }
```

**Response**
```json
{
  "answer": "최근 7일 데이터 기준...",
  "tools_used": ["get_recent_reviews", "search_by_keyword"],
  "game_name": "Counter-Strike 2"
}
```

---

## POC 실행

```bash
# 데모 모드 (예시 질문 3개 자동 실행)
python scripts/qa_pipeline.py --game "Elden Ring"

# 대화형 모드
python scripts/qa_pipeline.py --game "Elden Ring" --interactive

# 결과 파일 저장 (reports/qa-{날짜}-{게임슬러그}.md)
python scripts/qa_pipeline.py --game "Elden Ring" --interactive --save

# 수집 기간 조정
python scripts/qa_pipeline.py --game "Elden Ring" --days 14
```

POC는 DB 없이 Steam API에서 직접 데이터를 수집하여 동작한다.

---

## 체크리스트

- [x] `backend/analyzer/game_qa.py` — Tool 구현 + 에이전트 루프
- [x] `backend/schemas/qa.py` — QARequest / QAResponse Pydantic 스키마
- [x] `backend/api/qa.py` — POST /api/qa 엔드포인트
- [x] `backend/main.py` — qa_router 등록
- [x] `scripts/qa_pipeline.py` — DB 없이 실행 가능한 standalone POC
