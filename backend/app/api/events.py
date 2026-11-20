"""Read-only supporting-event endpoints."""

from fastapi import APIRouter, Depends, Query

from app.databases.mongodb import get_event_store
from app.schemas.events import EventRead
from app.utils.security import require_roles

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
def get_events(
    event_type: str | None = None,
    transaction_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    _user=Depends(require_roles("investigator", "administrator")),
) -> list[EventRead]:
    return [EventRead.model_validate(event) for event in get_event_store().list_events(event_type, transaction_id, limit)]
