"""
대응 제안 엔진 (Agent C)

이상 감지(Alert) 발생 시 Claude API를 호출하여
마케팅·CS·기획·사업 부서별 구체적인 대응 방안을 생성하고
Alert.recommendations 필드를 채운다.
"""
import json
import logging

import anthropic

from config import settings
from models.alert import Alert
from models.game import Game
from models.post import Post

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "당신은 게임 운영 전문 컨설턴트입니다. "
    "Steam 커뮤니티에서 감지된 이상 이슈를 바탕으로 "
    "각 부서가 즉시 실행 가능한 대응 방안을 한국어로 제안합니다. "
    "실질적이고 구체적인 액션 아이템 중심으로 작성하세요."
)

# alert_type → 한국어 설명
ALERT_TYPE_LABEL = {
    "sentiment_drop": "부정 리뷰 비율 급증",
    "volume_spike":   "리뷰 볼륨 급증",
    "keyword_alert":  "긴급 키워드 감지",
}

PROMPT_TEMPLATE = """게임: {game_name}
이슈 유형: {alert_type_label} ({alert_type})
심각도: {severity}
이슈 요약: {title}

[감지 상세 데이터]
{detail_text}

[관련 게시글 샘플 (최대 10건)]
{posts_sample}

위 이슈에 대해 아래 JSON 형식으로 각 부서별 대응 방안을 3가지씩 제안하세요.
JSON 외의 텍스트는 포함하지 마세요.

{{
  "summary": "이슈 원인 추정 및 핵심 대응 방향 2~3줄",
  "cs":        ["CS팀 대응 방안 1", "방안 2", "방안 3"],
  "planning":  ["기획팀 대응 방안 1", "방안 2", "방안 3"],
  "marketing": ["마케팅팀 대응 방안 1", "방안 2", "방안 3"],
  "business":  ["사업팀 대응 방안 1", "방안 2", "방안 3"]
}}"""


def _format_detail(detail: dict) -> str:
    lines = []
    for k, v in detail.items():
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.4f}")
        elif isinstance(v, list):
            lines.append(f"  {k}: {', '.join(str(i) for i in v)}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_posts_sample(posts: list[Post], limit: int = 10) -> str:
    # 인기순 상위 limit개, 리뷰 우선
    reviews = sorted(
        [p for p in posts if p.post_type == "review"],
        key=lambda p: p.like_count + p.comment_count,
        reverse=True,
    )[:limit]
    lines = []
    for i, post in enumerate(reviews, 1):
        label = "추천" if post.title == "Recommended" else "비추천"
        content_preview = (post.content or "")[:200]
        lines.append(f"[{i}] [{label}] {content_preview}")
    return "\n".join(lines) if lines else "(샘플 없음)"


async def fill_recommendations(
    alert: Alert,
    game: Game,
    current_posts: list[Post],
) -> None:
    """
    Alert.recommendations 필드를 Claude API 응답으로 채운다.
    DB commit은 호출자가 담당한다.
    """
    detail_text = _format_detail(alert.detail or {})
    posts_sample = _format_posts_sample(current_posts)

    prompt = PROMPT_TEMPLATE.format(
        game_name=game.name,
        alert_type_label=ALERT_TYPE_LABEL.get(alert.alert_type, alert.alert_type),
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        detail_text=detail_text,
        posts_sample=posts_sample,
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()

        # JSON 블록만 추출
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        alert.recommendations = json.loads(response_text)
        logger.info(f"[{game.name}] alert_id={alert.id} 대응 방안 생성 완료")

    except Exception as e:
        logger.error(f"[{game.name}] alert_id={alert.id} 대응 방안 생성 오류: {e}")
        # 실패해도 Alert 자체는 살아있어야 하므로 예외를 삼킨다
        alert.recommendations = {"error": str(e)}
