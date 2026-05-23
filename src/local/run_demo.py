from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from shared.models import FailedEvent, Incident, NormalizedEvent, SystemState
from shared.normalizer import normalize_event
from shared.rules import evaluate_reconciliation_rules
from shared.state_store import InMemoryStateStore
from shared.validator import validate_event


SAMPLES_DIR = PROJECT_ROOT / "samples"


def main() -> None:
    loaded_payloads = _load_sample_payloads(SAMPLES_DIR)
    valid_events: list[NormalizedEvent] = []
    failed_events: list[FailedEvent] = []

    for file_name, payload in loaded_payloads:
        validation = validate_event(payload)
        if not validation.is_valid:
            failed_events.append(_build_failed_event(file_name, payload, validation.errors))
            continue
        valid_events.append(normalize_event(payload))

    valid_events.sort(key=lambda event: event.timestamp)

    state_store = InMemoryStateStore()
    for event in valid_events:
        state_store.update(event)

    incidents = evaluate_reconciliation_rules(state_store.states_by_accession())

    _print_report(
        sample_dir=SAMPLES_DIR,
        events_loaded=len(loaded_payloads),
        events_processed=len(valid_events),
        failed_events=failed_events,
        incidents=incidents,
        states_by_accession=state_store.states_by_accession(),
    )


def _load_sample_payloads(sample_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    payloads: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(sample_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            payloads.append((path.name, json.load(file)))
    return payloads


def _build_failed_event(file_name: str, payload: dict[str, Any], errors: list[str]) -> FailedEvent:
    return FailedEvent(
        file_name=file_name,
        event_id=str(payload.get("eventId", "UNKNOWN")),
        source_system=str(payload.get("sourceSystem", "UNKNOWN")),
        message_type=str(payload.get("messageType", "UNKNOWN")),
        errors=errors,
    )


def _print_report(
    *,
    sample_dir: Path,
    events_loaded: int,
    events_processed: int,
    failed_events: list[FailedEvent],
    incidents: list[Incident],
    states_by_accession: dict[str, dict[str, SystemState]],
) -> None:
    print("Diagnostic Imaging Reconciliation - Phase 1 Local Demo")
    print("=" * 58)
    print(f"Sample directory: {sample_dir.relative_to(PROJECT_ROOT)}")
    print()
    print(f"Events loaded: {events_loaded}")
    print(f"Events processed: {events_processed}")
    print(f"Validation failures: {len(failed_events)}")
    print(f"Incidents created: {len(incidents)}")
    print(f"Failed events: {len(failed_events)}")

    print()
    print("Validation failures")
    print("-" * 19)
    if failed_events:
        for failed_event in failed_events:
            print(
                f"- {failed_event.event_id} ({failed_event.source_system} "
                f"{failed_event.message_type}) from {failed_event.file_name}"
            )
            for error in failed_event.errors:
                print(f"  Reason: {error}")
    else:
        print("None")

    print()
    print("Incidents")
    print("-" * 9)
    if incidents:
        for incident in incidents:
            print(f"- [{incident.severity}] {incident.rule_id}: {incident.title}")
            print(f"  Accession: {incident.accession_number}")
            print(f"  Details: {_format_details(incident.details)}")
            print(f"  Recommended action: {incident.recommended_action}")
    else:
        print("None")

    print()
    print("Current state by accession")
    print("-" * 26)
    for accession_number in sorted(states_by_accession):
        print(f"{accession_number}")
        for source_system in sorted(states_by_accession[accession_number]):
            state = states_by_accession[accession_number][source_system]
            print(
                "  "
                f"{source_system}: "
                f"examStatus={state.exam.get('examStatus', 'N/A')}, "
                f"reportStatus={state.report.get('reportStatus', 'N/A')}, "
                f"patient={state.patient.get('name', 'N/A')}, "
                f"ack={_format_ack(state)}"
            )


def _format_details(details: dict[str, object]) -> str:
    if not details:
        return "N/A"
    parts = []
    for key, value in details.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, sort_keys=True)
        parts.append(f"{key}={value}")
    return "; ".join(parts)


def _format_ack(state: SystemState) -> str:
    if not state.ack:
        return "N/A"
    expected = state.ack.get("expected")
    received = state.ack.get("received")
    return f"expected={expected}, received={received}"


if __name__ == "__main__":
    main()
