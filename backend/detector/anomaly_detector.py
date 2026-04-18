"""
이상 감지 엔진 (Agent A)

크롤링 완료 후 자동 실행되며, 게임별 커뮤니티 데이터에서
비정상적인 패턴을 감지하고 Alert를 생성한다.

감지 유형:
  - sentiment_drop  : 부정 리뷰 비율 급증
  - volume_spike    : 리뷰 볼륨 급증
  - keyword_alert   : 긴급 키워드 비율 급증
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.game import Game
from models.post import Post
from models.alert import Alert
from analyzer.action_recommender import fill_recommendations
from notifier.slack_notifier import send_alert

logger = logging.getLogger(__name__)

# 현재 윈도우: 최근 6시간 / 베이스라인: 직전 18시간
CURRENT_WINDOW_HOURS = 6
BASELINE_WINDOW_HOURS = 18

# 중복 알림 억제: 동일 게임·동일 타입 알림은 6시간 내 1회만
ALERT_COOLDOWN_HOURS = 6

# 감지 임계값
SENTIMENT_DROP_CRITICAL = 0.30   # 부정 비율 +30%p 이상 & 현재 60% 이상
SENTIMENT_DROP_WARNING  = 0.20   # 부정 비율 +20%p 이상 & 현재 50% 이상
SENTIMENT_MIN_REVIEWS   = 5      # 최소 리뷰 수 (데이터 부족 시 스킵)

VOLUME_SPIKE_CRITICAL   = 5.0    # 시간당 리뷰 수 기준 5배 이상
VOLUME_SPIKE_WARNING    = 3.0    # 시간당 리뷰 수 기준 3배 이상
VOLUME_MIN_CURRENT      = 10     # 현재 윈도우 최소 리뷰 수

CRITICAL_KEYWORDS = [
    "서버 점검", "접속 불가", "서버 다운", "환불", "refund",
    "server down", "banned", "핵", "hack", "exploit", "계정 정지",
]
WARNING_KEYWORDS = [
    "버그", "bug", "렉", "lag", "crash", "오류", "error",
    "disconnect", "튕김", "패치", "fix needed", "broken",
]
KEYWORD_CRITICAL_THRESHOLD = 0.10   # 전체 포스트의 10% 이상
KEYWORD_WARNING_THRESHOLD  = 0.15   # 전체 포스트의 15% 이상


def _negative_ratio(posts: list[Post]) -> tuple[float, int, int]:
    """리뷰 포스트에서 부정 비율을 계산한다. (ratio, negative_count, total_count)"""
    reviews = [p for p in posts if p.post_type == "review"]
    if not reviews:
        return 0.0, 0, 0
    negative = sum(1 for p in reviews if p.title == "Not Recommended")
    return negative / len(reviews), negative, len(reviews)


def _hourly_rate(posts: list[Post], window_hours: int) -> float:
    reviews = [p for p in posts if p.post_type == "review"]
    return len(reviews) / window_hours if window_hours > 0 else 0.0


def _keyword_ratio(posts: list[Post], keywords: list[str]) -> tuple[float, list[str]]:
    """포스트 제목+내용에서 키워드 매칭 비율과 매칭된 키워드 목록을 반환한다."""
    if not posts:
        return 0.0, []
    matched_posts = 0
    found_keywords: set[str] = set()
    for post in posts:
        text = f"{post.title or ''} {post.content or ''}".lower()
        hits = [kw for kw in keywords if kw.lower() in text]
        if hits:
            matched_posts += 1
            found_keywords.update(hits)
    return matched_posts / len(posts), list(found_keywords)


async def _is_duplicate(
    db: AsyncSession, game_id: int, alert_type: str
) -> bool:
    """동일 게임·타입의 알림이 ALERT_COOLDOWN_HOURS 내에 이미 존재하면 True."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)
    result = await db.execute(
        select(Alert)
        .where(Alert.game_id == game_id)
        .where(Alert.alert_type == alert_type)
        .where(Alert.detected_at >= cutoff)
    )
    return result.scalar_one_or_none() is not None


async def _create_alert(
    db: AsyncSession,
    game: Game,
    severity: str,
    alert_type: str,
    title: str,
    detail: dict,
    current_posts: list,
) -> Alert:
    alert = Alert(
        game_id=game.id,
        severity=severity,
        alert_type=alert_type,
        title=title,
        detail=detail,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    await db.flush()  # ID 확보 (commit은 호출자가 담당)

    # 대응 제안 즉시 생성 (Agent C)
    await fill_recommendations(alert, game, current_posts)

    return alert


async def detect_game_anomalies(
    db: AsyncSession, game: Game, now: datetime | None = None
) -> list[Alert]:
    """
    단일 게임에 대해 이상 감지를 수행하고 생성된 Alert 목록을 반환한다.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    current_start = now - timedelta(hours=CURRENT_WINDOW_HOURS)
    baseline_start = now - timedelta(hours=CURRENT_WINDOW_HOURS + BASELINE_WINDOW_HOURS)

    # 현재 윈도우 포스트
    current_result = await db.execute(
        select(Post)
        .where(Post.game_id == game.id)
        .where(Post.crawled_at >= current_start)
        .where(Post.crawled_at < now)
    )
    current_posts = current_result.scalars().all()

    # 베이스라인 윈도우 포스트
    baseline_result = await db.execute(
        select(Post)
        .where(Post.game_id == game.id)
        .where(Post.crawled_at >= baseline_start)
        .where(Post.crawled_at < current_start)
    )
    baseline_posts = baseline_result.scalars().all()

    created_alerts: list[Alert] = []

    # ── 1. Sentiment Drop 감지 ─────────────────────────────────────────
    curr_neg_ratio, curr_neg, curr_total = _negative_ratio(current_posts)
    base_neg_ratio, _, base_total = _negative_ratio(baseline_posts)

    if curr_total >= SENTIMENT_MIN_REVIEWS:
        diff = curr_neg_ratio - base_neg_ratio

        if diff >= SENTIMENT_DROP_CRITICAL and curr_neg_ratio >= 0.60:
            severity = "CRITICAL"
        elif diff >= SENTIMENT_DROP_WARNING and curr_neg_ratio >= 0.50:
            severity = "WARNING"
        else:
            severity = None

        if severity and not await _is_duplicate(db, game.id, "sentiment_drop"):
            alert = await _create_alert(
                db, game, severity, "sentiment_drop",
                f"[{game.name}] 부정 리뷰 비율 급증 ({base_neg_ratio:.0%} → {curr_neg_ratio:.0%}, +{diff:.0%}p)",
                {
                    "baseline_negative_ratio": round(base_neg_ratio, 4),
                    "current_negative_ratio": round(curr_neg_ratio, 4),
                    "diff": round(diff, 4),
                    "current_reviews": curr_total,
                    "baseline_reviews": base_total,
                    "window_hours": CURRENT_WINDOW_HOURS,
                },
                current_posts,
            )
            created_alerts.append(alert)
            logger.warning(f"[{game.name}] sentiment_drop {severity} 감지")

    # ── 2. Volume Spike 감지 ───────────────────────────────────────────
    curr_rate = _hourly_rate(current_posts, CURRENT_WINDOW_HOURS)
    base_rate = _hourly_rate(baseline_posts, BASELINE_WINDOW_HOURS)
    curr_review_count = len([p for p in current_posts if p.post_type == "review"])

    if base_rate > 0 and curr_review_count >= VOLUME_MIN_CURRENT:
        ratio = curr_rate / base_rate

        if ratio >= VOLUME_SPIKE_CRITICAL:
            severity = "CRITICAL"
        elif ratio >= VOLUME_SPIKE_WARNING:
            severity = "WARNING"
        else:
            severity = None

        if severity and not await _is_duplicate(db, game.id, "volume_spike"):
            alert = await _create_alert(
                db, game, severity, "volume_spike",
                f"[{game.name}] 리뷰 볼륨 급증 (평균 {base_rate:.1f}/h → {curr_rate:.1f}/h, {ratio:.1f}배)",
                {
                    "baseline_hourly_rate": round(base_rate, 2),
                    "current_hourly_rate": round(curr_rate, 2),
                    "ratio": round(ratio, 2),
                    "current_review_count": curr_review_count,
                    "window_hours": CURRENT_WINDOW_HOURS,
                },
                current_posts,
            )
            created_alerts.append(alert)
            logger.warning(f"[{game.name}] volume_spike {severity} 감지")

    # ── 3. Keyword Alert 감지 ──────────────────────────────────────────
    crit_ratio, crit_keywords = _keyword_ratio(current_posts, CRITICAL_KEYWORDS)
    warn_ratio, warn_keywords = _keyword_ratio(current_posts, WARNING_KEYWORDS)

    if crit_ratio >= KEYWORD_CRITICAL_THRESHOLD and crit_keywords:
        kw_severity = "CRITICAL"
        matched = crit_keywords
        ratio_val = crit_ratio
    elif warn_ratio >= KEYWORD_WARNING_THRESHOLD and warn_keywords:
        kw_severity = "WARNING"
        matched = warn_keywords
        ratio_val = warn_ratio
    else:
        kw_severity = None

    if kw_severity and not await _is_duplicate(db, game.id, "keyword_alert"):
        alert = await _create_alert(
            db, game, kw_severity, "keyword_alert",
            f"[{game.name}] 긴급 키워드 급증: {', '.join(matched[:3])}",
            {
                "matched_keywords": matched,
                "keyword_ratio": round(ratio_val, 4),
                "total_posts": len(current_posts),
                "window_hours": CURRENT_WINDOW_HOURS,
            },
            current_posts,
        )
        created_alerts.append(alert)
        logger.warning(f"[{game.name}] keyword_alert {kw_severity} 감지: {matched}")

    return created_alerts


async def detect_all_games(db: AsyncSession) -> list[Alert]:
    """
    모든 active 게임에 대해 이상 감지를 실행하고 생성된 Alert 전체를 반환한다.
    """
    games_result = await db.execute(select(Game).where(Game.is_active == True))
    games = games_result.scalars().all()

    all_alerts: list[Alert] = []
    now = datetime.now(timezone.utc)

    for game in games:
        try:
            alerts = await detect_game_anomalies(db, game, now)
            all_alerts.extend(alerts)
        except Exception as e:
            logger.error(f"[{game.name}] 이상 감지 오류: {e}")
            await db.rollback()
            continue

    if all_alerts:
        await db.commit()
        logger.info(f"이상 감지 완료: {len(all_alerts)}개 Alert 생성")

        # Slack 알림 전송 (TEAM 협업 프로토콜: commit 완료 후 Agent B 호출)
        games_result = await db.execute(select(Game).where(Game.is_active == True))
        games_by_id = {g.id: g for g in games_result.scalars().all()}
        for alert in all_alerts:
            game = games_by_id.get(alert.game_id)
            if game:
                await send_alert(alert, game, db)
    else:
        logger.info("이상 감지 완료: 감지된 이상 없음")

    return all_alerts
