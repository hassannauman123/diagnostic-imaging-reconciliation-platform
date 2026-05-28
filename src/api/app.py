from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException


SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shared.models import FailedEvent, Incident, NormalizedEvent, SystemState
from shared.normalizer import normalize_event
from shared.rules import evaluate_reconciliation_rules
from shared.state_store import InMemoryStateStore
from shared.validator import validate_event


app = FastAPI(
    title="Diagnostic Imaging Reconciliation API",
    description="Local Phase 2 API for synthetic diagnostic imaging reconciliation events.",
    version="0.2.0",
)

state_store = InMemoryStateStore()
failed_events: list[FailedEvent] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "2-local-api"}


@app.post("/events", status_code=202)
def ingest_event(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_event(payload)
    if not validation.is_valid:
        failed_event = _build_failed_event(payload, validation.errors)
        failed_events.append(failed_event)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Validation failed",
                "errors": validation.errors,
                "failedEvent": _failed_event_to_dict(failed_event),
            },
        )

    event = normalize_event(payload)
    state_store.update(event)
    incidents = _current_incidents()

    return {
        "message": "Event accepted",
        "eventId": event.event_id,
        "accessionNumber": event.accession_number,
        "sourceSystem": event.source_system,
        "messageType": event.message_type,
        "incidentCount": len(incidents),
    }


@app.get("/accessions/{accession_number}")
def get_accession(accession_number: str) -> dict[str, Any]:
    states = state_store.states_by_accession().get(accession_number)
    if states is None:
        raise HTTPException(status_code=404, detail=f"Accession not found: {accession_number}")

    accession_incidents = [
        incident
        for incident in _current_incidents()
        if incident.accession_number == accession_number
    ]

    return {
        "accessionNumber": accession_number,
        "systems": {
            source_system: _system_state_to_dict(state)
            for source_system, state in sorted(states.items())
        },
        "incidents": [_incident_to_dict(incident) for incident in accession_incidents],
    }


@app.get("/incidents")
def get_incidents() -> dict[str, Any]:
    incidents = _current_incidents()
    return {
        "count": len(incidents),
        "incidents": [_incident_to_dict(incident) for incident in incidents],
    }


@app.get("/events/{accession_number}")
def get_events(accession_number: str) -> dict[str, Any]:
    history = state_store.history_for_accession(accession_number)
    if not history:
        raise HTTPException(status_code=404, detail=f"No events found for accession: {accession_number}")

    return {
        "accessionNumber": accession_number,
        "count": len(history),
        "events": [_event_to_dict(event) for event in history],
    }


@app.get("/failed-events")
def get_failed_events() -> dict[str, Any]:
    return {
        "count": len(failed_events),
        "failedEvents": [_failed_event_to_dict(failed_event) for failed_event in failed_events],
    }


@app.post("/reset")
def reset_state() -> dict[str, str]:
    global state_store
    state_store = InMemoryStateStore()
    failed_events.clear()
    return {"message": "State reset"}


def _current_incidents() -> list[Incident]:
    return evaluate_reconciliation_rules(state_store.states_by_accession())


def _build_failed_event(payload: dict[str, Any], errors: list[str]) -> FailedEvent:
    return FailedEvent(
        file_name="API_REQUEST",
        event_id=str(payload.get("eventId", "UNKNOWN")),
        source_system=str(payload.get("sourceSystem", "UNKNOWN")),
        message_type=str(payload.get("messageType", "UNKNOWN")),
        errors=errors,
    )


def _system_state_to_dict(state: SystemState) -> dict[str, Any]:
    return {
        "accessionNumber": state.accession_number,
        "sourceSystem": state.source_system,
        "messageType": state.message_type,
        "lastUpdated": _timestamp_to_iso(state.last_updated),
        "sourceEventId": state.source_event_id,
        "patient": state.patient,
        "exam": state.exam,
        "report": state.report,
        "ack": state.ack,
    }


def _event_to_dict(event: NormalizedEvent) -> dict[str, Any]:
    return {
        "eventId": event.event_id,
        "sourceSystem": event.source_system,
        "messageType": event.message_type,
        "timestamp": event.timestamp_iso,
        "accessionNumber": event.accession_number,
        "patient": event.patient,
        "exam": event.exam,
        "report": event.report,
        "ack": event.ack,
    }


def _incident_to_dict(incident: Incident) -> dict[str, Any]:
    return {
        "incidentId": incident.incident_id,
        "ruleId": incident.rule_id,
        "accessionNumber": incident.accession_number,
        "severity": incident.severity,
        "title": incident.title,
        "description": incident.description,
        "recommendedAction": incident.recommended_action,
        "details": incident.details,
    }


def _failed_event_to_dict(failed_event: FailedEvent) -> dict[str, Any]:
    return {
        "fileName": failed_event.file_name,
        "eventId": failed_event.event_id,
        "sourceSystem": failed_event.source_system,
        "messageType": failed_event.message_type,
        "errors": failed_event.errors,
    }


def _timestamp_to_iso(value: Any) -> str:
    return value.isoformat().replace("+00:00", "Z")

