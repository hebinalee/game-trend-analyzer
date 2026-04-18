"""
로컬 파일 스토리지 레이어

크롤링 데이터와 분석 결과를 DB와 별개로 로컬 파일에 저장한다.
DB 장애 시 데이터 보존, 히스토리 재처리, 오프라인 분석 지원.

디렉터리 구조:
  {DATA_DIR}/
  ├── posts/
  │   └── {YYYY-MM-DD}/
  │       └── {app_id}.jsonl      # 포스트 1건 = JSON 1줄
  └── analysis/
      └── {YYYY-MM-DD}/
          └── {app_id}.json       # 분석 결과 전체
"""
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


def _posts_path(target_date: date, app_id: str) -> Path:
    return Path(settings.data_dir) / "posts" / str(target_date) / f"{app_id}.jsonl"


def _analysis_path(target_date: date, app_id: str) -> Path:
    return Path(settings.data_dir) / "analysis" / str(target_date) / f"{app_id}.json"


# ── Posts (JSONL) ──────────────────────────────────────────────────────────────

def save_posts(target_date: date, app_id: str, posts: list[dict]) -> Path:
    """
    크롤링 포스트 목록을 JSONL 파일로 저장한다.
    같은 날짜에 재호출하면 파일을 덮어쓴다 (멱등).
    """
    path = _posts_path(target_date, app_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for post in posts:
            # datetime 직렬화
            record = {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in post.items()
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"[file_store] posts 저장: {path} ({len(posts)}건)")
    return path


def load_posts(target_date: date, app_id: str) -> list[dict]:
    """JSONL 파일에서 포스트 목록을 읽는다. 파일 없으면 빈 리스트 반환."""
    path = _posts_path(target_date, app_id)
    if not path.exists():
        return []

    posts = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                posts.append(json.loads(line))
    return posts


def list_post_dates(app_id: str) -> list[date]:
    """특정 게임의 포스트 파일이 존재하는 날짜 목록을 반환한다."""
    base = Path(settings.data_dir) / "posts"
    if not base.exists():
        return []
    dates = []
    for day_dir in sorted(base.iterdir()):
        if (day_dir / f"{app_id}.jsonl").exists():
            try:
                dates.append(date.fromisoformat(day_dir.name))
            except ValueError:
                pass
    return dates


# ── Analysis (JSON) ────────────────────────────────────────────────────────────

def save_analysis(target_date: date, app_id: str, game_name: str, analysis: dict, post_count: int) -> Path:
    """
    LLM 분석 결과를 JSON 파일로 저장한다.
    같은 날짜에 재호출하면 파일을 덮어쓴다 (멱등).
    """
    path = _analysis_path(target_date, app_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "app_id": app_id,
        "game_name": game_name,
        "report_date": str(target_date),
        "post_count": post_count,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **analysis,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[file_store] analysis 저장: {path}")
    return path


def load_analysis(target_date: date, app_id: str) -> dict | None:
    """JSON 파일에서 분석 결과를 읽는다. 파일 없으면 None 반환."""
    path = _analysis_path(target_date, app_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_analysis_dates(app_id: str) -> list[date]:
    """특정 게임의 분석 파일이 존재하는 날짜 목록을 반환한다."""
    base = Path(settings.data_dir) / "analysis"
    if not base.exists():
        return []
    dates = []
    for day_dir in sorted(base.iterdir()):
        if (day_dir / f"{app_id}.json").exists():
            try:
                dates.append(date.fromisoformat(day_dir.name))
            except ValueError:
                pass
    return dates


# ── 유틸 ───────────────────────────────────────────────────────────────────────

def data_summary() -> dict:
    """저장된 데이터 현황 요약 (관리용)."""
    base = Path(settings.data_dir)
    posts_base    = base / "posts"
    analysis_base = base / "analysis"

    post_files = list(posts_base.rglob("*.jsonl")) if posts_base.exists() else []
    analysis_files = list(analysis_base.rglob("*.json")) if analysis_base.exists() else []

    total_posts = sum(
        sum(1 for line in f.open(encoding="utf-8") if line.strip())
        for f in post_files
    )

    return {
        "data_dir": str(base.resolve()),
        "post_files": len(post_files),
        "total_posts": total_posts,
        "analysis_files": len(analysis_files),
        "post_dates": sorted({f.parent.name for f in post_files}),
        "analysis_dates": sorted({f.parent.name for f in analysis_files}),
    }
