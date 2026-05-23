from __future__ import annotations

from shared.models import Incident


class IncidentBuilder:
    def __init__(self) -> None:
        self._next_number = 1

    def create(
        self,
        *,
        rule_id: str,
        accession_number: str,
        severity: str,
        title: str,
        description: str,
        recommended_action: str,
        details: dict[str, object] | None = None,
    ) -> Incident:
        incident = Incident(
            incident_id=f"inc-{self._next_number:04d}",
            rule_id=rule_id,
            accession_number=accession_number,
            severity=severity,
            title=title,
            description=description,
            recommended_action=recommended_action,
            details=details or {},
        )
        self._next_number += 1
        return incident

