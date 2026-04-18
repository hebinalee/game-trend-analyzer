"""
Slack 알림 엔진 (Agent B)

Alert commit 직후 호출되며, Slack Incoming Webhook으로 알림을 전송한다.
- CRITICAL: 감지 수치 + 부서별 대응 방안 전체 포함
- WARNING : 요약 메시지만 전송
전송 성공 시 Alert.notified = True 업데이트.
SLACK_WEBHOOK_URL 미설정 시 전송 없이 로그만 남김 (TEAM 운영 원칙: 장애 격리).
"""
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.alert import Alert
from models.game import Game

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}
ALERT_TYPE_LABEL = {
    "sentiment_drop": "부정 리뷰 비율 급증",
    "volume_spike":   "리뷰 볼륨 급증",
    "keyword_alert":  "긴급 키워드 감지",
}
DEPT_LABEL = {"cs": "CS", "planning": "기획", "marketing": "마케팅", "business": "사업"}


# ── Block Kit 빌더 ────────────────────────────────────────────────────────────

def _header_block(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def _section_block(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _fields_block(fields: list[tuple[str, str]]) -> dict:
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields],
    }


def _divider() -> dict:
    return {"type": "divider"}


def _action_button(label: str, url: str) -> dict:
    return {
        "type": "actions",
        "elements": [{"type": "button", "text": {"type": "plain_text", "text": label}, "url": url}],
    }


def _build_detail_fields(alert: Alert) -> list[tuple[str, str]]:
    """alert_type별로 핵심 수치를 Block Kit fields 형태로 반환한다."""
    d = alert.detail or {}
    if alert.alert_type == "sentiment_drop":
        return [
            ("현재 부정 비율", f"{d.get('current_negative_ratio', 0):.0%} ({d.get('current_reviews', '-')}건)"),
            ("직전 부정 비율", f"{d.get('baseline_negative_ratio', 0):.0%} ({d.get('baseline_reviews', '-')}건)"),
            ("변화량", f"+{d.get('diff', 0):.0%}p"),
            ("감지 윈도우", f"최근 {d.get('window_hours', 6)}시간"),
        ]
    if alert.alert_type == "volume_spike":
        return [
            ("현재 리뷰 수", f"{d.get('current_review_count', '-')}건 ({d.get('current_hourly_rate', 0):.1f}/h)"),
            ("평균 리뷰 수", f"{d.get('baseline_hourly_rate', 0):.1f}/h"),
            ("급증 배율", f"{d.get('ratio', 0):.1f}배"),
            ("감지 윈도우", f"최근 {d.get('window_hours', 6)}시간"),
        ]
    if alert.alert_type == "keyword_alert":
        keywords = ", ".join(d.get("matched_keywords", [])[:5])
        return [
            ("감지 키워드", keywords or "-"),
            ("키워드 비율", f"{d.get('keyword_ratio', 0):.0%} (전체 {d.get('total_posts', '-')}건 중)"),
            ("감지 윈도우", f"최근 {d.get('window_hours', 6)}시간"),
        ]
    return []


def _build_recommendations_text(recs: dict) -> str:
    lines = []
    for key, label in DEPT_LABEL.items():
        items = recs.get(key, [])
        if items:
            lines.append(f"*{label}*: {items[0]}")
    return "\n".join(lines)


def _build_critical_blocks(alert: Alert, game: Game) -> list[dict]:
    emoji = SEVERITY_EMOJI.get(alert.severity, "🔔")
    type_label = ALERT_TYPE_LABEL.get(alert.alert_type, alert.alert_type)
    alert_url = f"{settings.dashboard_url}/alerts/{alert.id}"
    recs = alert.recommendations or {}

    blocks = [
        _header_block(f"{emoji} CRITICAL 이슈 감지 — {game.name}"),
        _section_block(f"*{type_label}*\n{alert.title}"),
        _divider(),
        _fields_block(_build_detail_fields(alert)),
    ]

    if summary := recs.get("summary"):
        blocks.append(_divider())
        blocks.append(_section_block(f"*핵심 대응 방향*\n{summary}"))

    dept_text = _build_recommendations_text(recs)
    if dept_text:
        blocks.append(_section_block(f"*부서별 대응 방안 (1순위)*\n{dept_text}"))

    blocks.append(_divider())
    blocks.append(_action_button("대시보드에서 전체 보기 →", alert_url))
    return blocks


def _build_warning_blocks(alert: Alert, game: Game) -> list[dict]:
    emoji = SEVERITY_EMOJI.get(alert.severity, "⚠️")
    type_label = ALERT_TYPE_LABEL.get(alert.alert_type, alert.alert_type)
    alert_url = f"{settings.dashboard_url}/alerts/{alert.id}"

    return [
        _section_block(f"{emoji} *[{game.name}] WARNING — {type_label}*\n> {alert.title}"),
        _action_button("대시보드 →", alert_url),
    ]


# ── 전송 함수 ─────────────────────────────────────────────────────────────────

async def send_alert(alert: Alert, game: Game, db: AsyncSession) -> None:
    """
    Alert를 Slack으로 전송하고 성공 시 alert.notified = True로 업데이트한다.
    SLACK_WEBHOOK_URL 미설정 또는 전송 실패 시 예외를 삼키고 로깅한다 (장애 격리).
    """
    if not settings.slack_webhook_url:
        logger.info(f"[{game.name}] SLACK_WEBHOOK_URL 미설정, 알림 스킵 (alert_id={alert.id})")
        return

    if alert.severity == "CRITICAL":
        blocks = _build_critical_blocks(alert, game)
    else:
        blocks = _build_warning_blocks(alert, game)

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.slack_webhook_url, json=payload)
            resp.raise_for_status()

        alert.notified = True
        await db.commit()
        logger.info(f"[{game.name}] Slack 알림 전송 완료 (alert_id={alert.id}, severity={alert.severity})")

    except Exception as e:
        logger.error(f"[{game.name}] Slack 알림 전송 실패 (alert_id={alert.id}): {e}")
        # notified=False 유지 → 재시도 스케줄러가 처리


async def retry_failed_notifications(db: AsyncSession) -> None:
    """
    notified=False인 미전송 Alert를 재시도한다.
    스케줄러에서 1시간 주기로 호출된다.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from models.game import Game as GameModel

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)  # 24h 초과는 재시도 안 함

    result = await db.execute(
        select(Alert)
        .where(Alert.notified == False)
        .where(Alert.detected_at >= cutoff)
        .order_by(Alert.detected_at.desc())
    )
    pending = result.scalars().all()

    if not pending:
        return

    logger.info(f"미전송 Alert 재시도: {len(pending)}건")
    for alert in pending:
        game_result = await db.execute(
            select(GameModel).where(GameModel.id == alert.game_id)
        )
        game = game_result.scalar_one_or_none()
        if game:
            await send_alert(alert, game, db)
