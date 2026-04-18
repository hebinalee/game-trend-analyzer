"""
파일 → DB 동기화

로컬 파일에 저장된 포스트·분석 결과를 PostgreSQL에 upsert한다.
DB 장애 복구, 신규 DB 초기화, 히스토리 재처리에 사용.
"""
import logging
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.game import Game
from models.post import Post
from models.report import Report
from storage.file_store import load_posts, load_analysis, list_post_dates, list_analysis_dates

logger = logging.getLogger(__name__)


async def _get_game_by_app_id(db: AsyncSession, app_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.app_id == app_id))
    return result.scalar_one_or_none()


async def sync_posts_to_db(db: AsyncSession, target_date: date, app_id: str) -> int:
    """
    특정 날짜·게임의 JSONL 파일을 읽어 posts 테이블에 upsert한다.
    반환값: 신규 삽입된 건수
    """
    posts_data = load_posts(target_date, app_id)
    if not posts_data:
        logger.info(f"[db_sync] 파일 없음: posts/{target_date}/{app_id}.jsonl")
        return 0

    game = await _get_game_by_app_id(db, app_id)
    if not game:
        logger.warning(f"[db_sync] DB에 app_id={app_id} 게임 없음, 스킵")
        return 0

    inserted = 0
    for record in posts_data:
        existing = await db.execute(
            select(Post).where(Post.post_id == record["post_id"])
        )
        if existing.scalar_one_or_none():
            continue

        def parse_dt(val):
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val.replace("Z", "+00:00"))

        db.add(Post(
            game_id=game.id,
            post_id=record["post_id"],
            title=record.get("title"),
            content=record.get("content"),
            author=record.get("author"),
            like_count=record.get("like_count", 0),
            comment_count=record.get("comment_count", 0),
            post_type=record.get("post_type"),
            crawled_at=parse_dt(record.get("crawled_at")),
            posted_at=parse_dt(record.get("posted_at")),
        ))
        inserted += 1

    await db.commit()
    logger.info(f"[db_sync] posts 동기화 완료: {app_id}/{target_date} — {inserted}건 신규 삽입 ({len(posts_data)}건 처리)")
    return inserted


async def sync_analysis_to_db(db: AsyncSession, target_date: date, app_id: str) -> bool:
    """
    특정 날짜·게임의 분석 JSON 파일을 읽어 reports 테이블에 upsert한다.
    반환값: 성공 여부
    """
    analysis = load_analysis(target_date, app_id)
    if not analysis:
        logger.info(f"[db_sync] 파일 없음: analysis/{target_date}/{app_id}.json")
        return False

    game = await _get_game_by_app_id(db, app_id)
    if not game:
        logger.warning(f"[db_sync] DB에 app_id={app_id} 게임 없음, 스킵")
        return False

    stmt = pg_insert(Report).values(
        game_id=game.id,
        report_date=target_date,
        summary=analysis.get("summary"),
        hot_topics=analysis.get("hot_topics"),
        sentiment=analysis.get("sentiment"),
        key_issues=analysis.get("key_issues"),
        trend_keywords=analysis.get("trend_keywords"),
        raw_post_count=analysis.get("post_count", 0),
        created_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        constraint="uq_game_report_date",
        set_={
            "summary": analysis.get("summary"),
            "hot_topics": analysis.get("hot_topics"),
            "sentiment": analysis.get("sentiment"),
            "key_issues": analysis.get("key_issues"),
            "trend_keywords": analysis.get("trend_keywords"),
            "raw_post_count": analysis.get("post_count", 0),
            "created_at": datetime.now(timezone.utc),
        },
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(f"[db_sync] analysis 동기화 완료: {app_id}/{target_date}")
    return True


async def sync_date_to_db(db: AsyncSession, target_date: date) -> dict:
    """
    특정 날짜의 모든 게임 파일을 DB에 동기화한다.
    반환: {app_id: {"posts": int, "analysis": bool}}
    """
    from config import settings
    from pathlib import Path

    app_ids: set[str] = set()
    posts_dir = Path(settings.data_dir) / "posts" / str(target_date)
    analysis_dir = Path(settings.data_dir) / "analysis" / str(target_date)

    if posts_dir.exists():
        app_ids |= {p.stem for p in posts_dir.glob("*.jsonl")}
    if analysis_dir.exists():
        app_ids |= {p.stem for p in analysis_dir.glob("*.json")}

    results = {}
    for app_id in sorted(app_ids):
        try:
            posts_count = await sync_posts_to_db(db, target_date, app_id)
            analysis_ok = await sync_analysis_to_db(db, target_date, app_id)
            results[app_id] = {"posts": posts_count, "analysis": analysis_ok}
        except Exception as e:
            await db.rollback()
            logger.error(f"[db_sync] {app_id}/{target_date} 동기화 오류: {e}")
            results[app_id] = {"error": str(e)}

    return results


async def sync_all_to_db(db: AsyncSession) -> dict:
    """
    로컬에 저장된 모든 날짜의 데이터를 DB에 동기화한다.
    신규 DB 초기화나 전체 복구에 사용.
    """
    from config import settings
    from pathlib import Path

    base = Path(settings.data_dir)
    all_dates: set[date] = set()

    for sub in ["posts", "analysis"]:
        sub_dir = base / sub
        if sub_dir.exists():
            for day_dir in sub_dir.iterdir():
                try:
                    all_dates.add(date.fromisoformat(day_dir.name))
                except ValueError:
                    pass

    all_results = {}
    for target_date in sorted(all_dates):
        logger.info(f"[db_sync] {target_date} 동기화 시작")
        all_results[str(target_date)] = await sync_date_to_db(db, target_date)

    logger.info(f"[db_sync] 전체 동기화 완료: {len(all_dates)}일치 처리")
    return all_results
