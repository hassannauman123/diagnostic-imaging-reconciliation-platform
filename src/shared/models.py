from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FailedEvent:
    file_name: str
    event_id: str
    source_system: str
    message_type: str
    errors: list[str]


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    source_system: str
    message_type: str
    timestamp: datetime
    accession_number: str
    patient: JsonDict = field(default_factory=dict)
    exam: JsonDict = field(default_factory=dict)
    report: JsonDict = field(default_factory=dict)
    ack: JsonDict = field(default_factory=dict)
    raw_event: JsonDict = field(default_factory=dict)

    @property
    def timestamp_iso(self) -> str:
        return self.timestamp.isoformat().replace("+00:00", "Z")


@dataclass
class SystemState:
    accession_number: str
    source_system: str
    message_type: str
    last_updated: datetime
    source_event_id: str
    patient: JsonDict = field(default_factory=dict)
    exam: JsonDict = field(default_factory=dict)
    report: JsonDict = field(default_factory=dict)
    ack: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class Incident:
    incident_id: str
    rule_id: str
    accession_number: str
    severity: str
    title: str
    description: str
    recommended_action: str
    details: JsonDict = field(default_factory=dict)

