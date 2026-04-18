from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.alert import Alert
from models.game import Game
from schemas.alert import AlertListItem, AlertDetail, AlertStatusUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# 허용된 상태 전환 (spec: 역방향 불가)
VALID_TRANSITIONS = {
    "new": "acknowledged",
    "acknowledged": "resolved",
}


def _attach_game_name(alert: Alert, game: Game) -> dict:
    """SQLAlchemy 내부 속성(_sa_instance_state 등)을 제외하고 직렬화 가능한 dict를 반환한다."""
    return {
        "id": alert.id,
        "game_id": alert.game_id,
        "game_name": game.name,
        "severity": alert.severity,
        "alert_type": alert.alert_type,
        "title": alert.title,
        "detail": alert.detail,
        "recommendations": alert.recommendations,
        "status": alert.status,
        "notified": alert.notified,
        "detected_at": alert.detected_at,
    }


@router.get("", response_model=list[AlertListItem])
async def get_alerts(
    game_id: int | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """이슈 목록 조회. game_id / severity / status 로 필터링."""
    query = select(Alert, Game).join(Game, Alert.game_id == Game.id)
    if game_id is not None:
        query = query.where(Alert.game_id == game_id)
    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)
    query = query.order_by(Alert.detected_at.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()
    return [_attach_game_name(alert, game) for alert, game in rows]


@router.get("/unread-count")
async def get_unread_count(db: AsyncSession = Depends(get_db)):
    """미확인(new) Alert 수 요약. 헤더 배지 용도."""
    result = await db.execute(
        select(Alert).where(Alert.status == "new")
    )
    alerts = result.scalars().all()
    critical = sum(1 for a in alerts if a.severity == "CRITICAL")
    return {"total": len(alerts), "critical": critical}


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert_detail(alert_id: int, db: AsyncSession = Depends(get_db)):
    """이슈 상세 조회 (detail + recommendations 포함)."""
    result = await db.execute(
        select(Alert, Game)
        .join(Game, Alert.game_id == Game.id)
        .where(Alert.id == alert_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert를 찾을 수 없습니다.")
    alert, game = row
    return _attach_game_name(alert, game)


@router.patch("/{alert_id}/status", response_model=AlertDetail)
async def update_alert_status(
    alert_id: int,
    body: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """이슈 상태 변경. 허용 전환: new→acknowledged, acknowledged→resolved."""
    result = await db.execute(
        select(Alert, Game)
        .join(Game, Alert.game_id == Game.id)
        .where(Alert.id == alert_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert를 찾을 수 없습니다.")
    alert, game = row

    allowed_next = VALID_TRANSITIONS.get(alert.status)
    if body.status != allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"'{alert.status}' 상태에서 '{body.status}'로 전환할 수 없습니다. 허용: {allowed_next}",
        )

    alert.status = body.status
    await db.commit()
    await db.refresh(alert)
    return _attach_game_name(alert, game)
