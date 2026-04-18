from datetime import datetime
from typing import Any
from pydantic import BaseModel


class AlertListItem(BaseModel):
    id: int
    game_id: int
    game_name: str
    severity: str
    alert_type: str
    title: str
    status: str
    notified: bool
    detected_at: datetime

    class Config:
        from_attributes = True


class AlertDetail(BaseModel):
    id: int
    game_id: int
    game_name: str
    severity: str
    alert_type: str
    title: str
    detail: dict[str, Any] | None = None
    recommendations: dict[str, Any] | None = None
    status: str
    notified: bool
    detected_at: datetime

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str  # acknowledged | resolved
