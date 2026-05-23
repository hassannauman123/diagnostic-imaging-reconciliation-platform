from __future__ import annotations

from collections import defaultdict

from shared.models import NormalizedEvent, SystemState


class InMemoryStateStore:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, SystemState]] = defaultdict(dict)
        self._history: dict[str, list[NormalizedEvent]] = defaultdict(list)

    def update(self, event: NormalizedEvent) -> None:
        accession_states = self._states[event.accession_number]
        current_state = accession_states.get(event.source_system)

        # Keep the latest known state per accession/source even if files are loaded out of order.
        if current_state is None or event.timestamp >= current_state.last_updated:
            accession_states[event.source_system] = SystemState(
                accession_number=event.accession_number,
                source_system=event.source_system,
                message_type=event.message_type,
                last_updated=event.timestamp,
                source_event_id=event.event_id,
                patient=event.patient,
                exam=event.exam,
                report=event.report,
                ack=event.ack,
            )

        self._history[event.accession_number].append(event)
        self._history[event.accession_number].sort(key=lambda item: item.timestamp)

    def states_by_accession(self) -> dict[str, dict[str, SystemState]]:
        return {accession: dict(states) for accession, states in self._states.items()}

    def history_for_accession(self, accession_number: str) -> list[NormalizedEvent]:
        return list(self._history.get(accession_number, []))

