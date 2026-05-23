from __future__ import annotations

from shared.incident_builder import IncidentBuilder
from shared.models import Incident, SystemState


COMPLETE_RIS_STATUSES = {"FINAL", "COMPLETE", "COMPLETED", "REPORTED"}
REPORTING_SYSTEMS = {"POWERSCRIBE", "REPORTING"}


def evaluate_reconciliation_rules(
    states_by_accession: dict[str, dict[str, SystemState]],
) -> list[Incident]:
    builder = IncidentBuilder()
    incidents: list[Incident] = []

    for accession_number in sorted(states_by_accession):
        states = states_by_accession[accession_number]
        incidents.extend(_rule_001_blank_exam_description(accession_number, states, builder))
        incidents.extend(_rule_002_final_report_mismatch(accession_number, states, builder))
        incidents.extend(_rule_003_stale_patient_demographics(accession_number, states, builder))
        incidents.extend(_rule_004_missing_downstream_ack(accession_number, states, builder))
        incidents.extend(_rule_005_conflicting_accession_state(accession_number, states, builder))

    return incidents


def _rule_001_blank_exam_description(
    accession_number: str,
    states: dict[str, SystemState],
    builder: IncidentBuilder,
) -> list[Incident]:
    ris = states.get("RIS")
    if not ris:
        return []

    ris_description = _clean_string(ris.exam.get("examDescription"))
    if not ris_description:
        return []

    incidents: list[Incident] = []
    for source_system, state in states.items():
        if source_system not in REPORTING_SYSTEMS:
            continue
        reporting_description = _clean_string(state.exam.get("examDescription"))
        if not reporting_description:
            incidents.append(
                builder.create(
                    rule_id="RULE_001_BLANK_EXAM_DESCRIPTION",
                    accession_number=accession_number,
                    severity="MEDIUM",
                    title="Blank exam description in PowerScribe while RIS has valid exam description",
                    description=(
                        "RIS has a populated exam description, but the reporting system state is blank."
                    ),
                    recommended_action=(
                        "Check order/report mapping and resend corrected exam update to reporting system."
                    ),
                    details={
                        "risExamDescription": ris_description,
                        "reportingSystem": source_system,
                        "reportingExamDescription": state.exam.get("examDescription", ""),
                    },
                )
            )
    return incidents


def _rule_002_final_report_mismatch(
    accession_number: str,
    states: dict[str, SystemState],
    builder: IncidentBuilder,
) -> list[Incident]:
    ris = states.get("RIS")
    if not ris:
        return []

    ris_status = _clean_string(ris.exam.get("examStatus")).upper()
    incidents: list[Incident] = []

    for source_system, state in states.items():
        if source_system not in REPORTING_SYSTEMS:
            continue
        report_status = _clean_string(state.report.get("reportStatus")).upper()
        if report_status == "FINAL" and ris_status not in COMPLETE_RIS_STATUSES:
            incidents.append(
                builder.create(
                    rule_id="RULE_002_FINAL_REPORT_MISMATCH",
                    accession_number=accession_number,
                    severity="HIGH",
                    title="PowerScribe report is final but RIS is still pending or incomplete",
                    description=(
                        "The reporting system shows a final report, but RIS has not reached a complete "
                        "or reported status."
                    ),
                    recommended_action=(
                        "Review report finalization message flow and verify RIS received/report status update."
                    ),
                    details={
                        "risExamStatus": ris.exam.get("examStatus"),
                        "reportingSystem": source_system,
                        "reportingReportStatus": state.report.get("reportStatus"),
                    },
                )
            )
    return incidents


def _rule_003_stale_patient_demographics(
    accession_number: str,
    states: dict[str, SystemState],
    builder: IncidentBuilder,
) -> list[Incident]:
    ris = states.get("RIS")
    if not ris or not ris.patient:
        return []

    stale_systems: list[str] = []
    stale_system_details: list[dict[str, object]] = []
    details: dict[str, object] = {
        "risPatient": ris.patient,
        "staleSystems": stale_system_details,
    }

    for source_system, state in states.items():
        if source_system == "RIS" or not state.patient:
            continue
        if state.last_updated >= ris.last_updated:
            continue
        if _patient_differs(ris.patient, state.patient):
            stale_systems.append(source_system)
            stale_system_details.append(
                {
                    "sourceSystem": source_system,
                    "patient": state.patient,
                    "lastUpdated": state.last_updated.isoformat().replace("+00:00", "Z"),
                }
            )

    if not stale_systems:
        return []

    return [
        builder.create(
            rule_id="RULE_003_STALE_PATIENT_DEMOGRAPHICS",
            accession_number=accession_number,
            severity="HIGH",
            title="Patient demographics are stale across systems",
            description=(
                "RIS has newer or different patient demographics than downstream system state for this accession."
            ),
            recommended_action=(
                "Review patient update propagation and confirm downstream systems received the latest demographic update."
            ),
            details=details,
        )
    ]


def _rule_004_missing_downstream_ack(
    accession_number: str,
    states: dict[str, SystemState],
    builder: IncidentBuilder,
) -> list[Incident]:
    incidents: list[Incident] = []

    for source_system, state in states.items():
        expected = state.ack.get("expected")
        received = state.ack.get("received")
        if expected is True and received is False:
            incidents.append(
                builder.create(
                    rule_id="RULE_004_MISSING_DOWNSTREAM_ACK",
                    accession_number=accession_number,
                    severity="MEDIUM",
                    title="Downstream acknowledgement missing",
                    description="A downstream acknowledgement was expected but has not been received.",
                    recommended_action=(
                        "Check downstream message delivery and acknowledgement handling."
                    ),
                    details={
                        "sourceSystem": source_system,
                        "targetSystem": state.ack.get("targetSystem"),
                        "ackExpected": expected,
                        "ackReceived": received,
                    },
                )
            )

    return incidents


def _rule_005_conflicting_accession_state(
    accession_number: str,
    states: dict[str, SystemState],
    builder: IncidentBuilder,
) -> list[Incident]:
    ris = states.get("RIS")
    if not ris:
        return []

    ris_status = _clean_string(ris.exam.get("examStatus")).upper()
    if ris_status not in {"CANCELLED", "CANCELED"}:
        return []

    conflicting_systems: list[str] = []
    for source_system, state in states.items():
        if source_system == "RIS":
            continue

        exam_status = _clean_string(state.exam.get("examStatus")).upper()
        report_status = _clean_string(state.report.get("reportStatus")).upper()
        if exam_status in {"IMAGES_AVAILABLE", "IN_PROGRESS", "COMPLETED"} or report_status == "FINAL":
            conflicting_systems.append(source_system)

    if not conflicting_systems:
        return []

    return [
        builder.create(
            rule_id="RULE_005_CONFLICTING_ACCESSION_STATE",
            accession_number=accession_number,
            severity="CRITICAL",
            title="Same accession number has conflicting state across systems",
            description=(
                "RIS indicates a cancelled accession while another system still has active images, "
                "workflow, or final reporting state."
            ),
            recommended_action=(
                "Investigate workflow state drift across systems and reconcile source-of-truth status."
            ),
            details={
                "risExamStatus": ris.exam.get("examStatus"),
                "conflictingSystems": conflicting_systems,
            },
        )
    ]


def _clean_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _patient_differs(ris_patient: dict[str, object], other_patient: dict[str, object]) -> bool:
    for field_name in ("patientId", "name", "dateOfBirth"):
        if _clean_string(ris_patient.get(field_name)) != _clean_string(other_patient.get(field_name)):
            return True
    return False
