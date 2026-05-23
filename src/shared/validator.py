from __future__ import annotations

from datetime import datetime
from typing import Any

from shared.models import ValidationResult


REQUIRED_FIELDS = ("eventId", "sourceSystem", "messageType", "timestamp", "accessionNumber")


def validate_event(payload: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []

    for field_name in REQUIRED_FIELDS:
        value = payload.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing required field: {field_name}")

    timestamp = payload.get("timestamp")
    if timestamp and not _is_iso_timestamp(str(timestamp)):
        errors.append("Malformed timestamp: expected ISO-8601 value")

    return ValidationResult(is_valid=not errors, errors=errors)


def _is_iso_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True

