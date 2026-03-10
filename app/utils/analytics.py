import json
from typing import Any

from app.models import AnalyticsEvent


async def track_event(
    session: Any,
    event: str,
    tool: str,
    session_id: str,
    metadata: dict,
    utm_source: str = "",
    utm_campaign: str = "",
) -> None:
    """Async: save an analytics event to the database."""
    record = AnalyticsEvent(
        event=event,
        tool=tool,
        session_id=session_id,
        metadata_json=json.dumps(metadata),
        utm_source=utm_source,
        utm_campaign=utm_campaign,
    )
    session.add(record)
    await session.commit()
