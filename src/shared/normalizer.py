from __future__ import annotations

from datetime import datetime
from typing import Any

from shared.models import NormalizedEvent


def normalize_event(payload: dict[str, Any]) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=str(payload["eventId"]).strip(),
        source_system=str(payload["sourceSystem"]).strip().upper(),
        message_type=str(payload["messageType"]).strip().upper(),
        timestamp=_parse_timestamp(str(payload["timestamp"])),
        accession_number=str(payload["accessionNumber"]).strip(),
        patient=_dict_or_empty(payload.get("patient")),
        exam=_dict_or_empty(payload.get("exam")),
        report=_dict_or_empty(payload.get("report")),
        ack=_dict_or_empty(payload.get("ack")),
        raw_event=payload,
    )


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}

