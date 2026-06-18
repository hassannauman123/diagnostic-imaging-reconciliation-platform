from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3

from shared.models import SystemState
from shared.rules import evaluate_reconciliation_rules


dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

STATE_TABLE_NAME = os.environ["STATE_TABLE_NAME"]
INCIDENTS_TABLE_NAME = os.environ["INCIDENTS_TABLE_NAME"]
ALERT_TOPIC_ARN = os.environ["ALERT_TOPIC_ARN"]

state_table = dynamodb.Table(STATE_TABLE_NAME)
incidents_table = dynamodb.Table(INCIDENTS_TABLE_NAME)

ALERT_SEVERITIES = {"HIGH", "CRITICAL"}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", "unknown")
    accession_number = _extract_accession_number(event)

    print(
        json.dumps(
            {
                "message": "reconciliation_started",
                "requestId": request_id,
                "accessionNumber": accession_number,
            }
        )
    )

    states = _load_states_for_accession(accession_number)
    incidents = evaluate_reconciliation_rules({accession_number: states})

    stored_incidents: list[dict[str, Any]] = []
    for incident in incidents:
        item = _incident_to_item(incident, request_id)
        _store_incident(item)
        stored_incidents.append(item)

        if item["severity"] in ALERT_SEVERITIES:
            _publish_alert(item)

    print(
        json.dumps(
            {
                "message": "reconciliation_completed",
                "requestId": request_id,
                "accessionNumber": accession_number,
                "systemCount": len(states),
                "incidentCount": len(stored_incidents),
            }
        )
    )

    return {
        "accessionNumber": accession_number,
        "systemCount": len(states),
        "incidentCount": len(stored_incidents),
        "incidents": [
            {
                "incidentId": item["incidentId"],
                "ruleId": item["ruleId"],
                "severity": item["severity"],
                "title": item["title"],
            }
            for item in stored_incidents
        ],
    }


def _extract_accession_number(event: dict[str, Any]) -> str:
    accession_number = event.get("accessionNumber")
    if not accession_number:
        raise ValueError("accessionNumber is required")
    return str(accession_number)


def _load_states_for_accession(accession_number: str) -> dict[str, SystemState]:
    response = state_table.query(
        KeyConditionExpression="accessionNumber = :accession",
        ExpressionAttributeValues={":accession": accession_number},
    )

    states: dict[str, SystemState] = {}
    for item in response.get("Items", []):
        source_system = str(item["sourceSystem"])
        states[source_system] = SystemState(
            accession_number=str(item["accessionNumber"]),
            source_system=source_system,
            message_type=str(item.get("messageType", "")),
            last_updated=_parse_timestamp(str(item["lastUpdated"])),
            source_event_id=str(item.get("sourceEventId", "")),
            patient=_dict_or_empty(item.get("patient")),
            exam=_dict_or_empty(item.get("exam")),
            report=_dict_or_empty(item.get("report")),
            ack=_dict_or_empty(item.get("ack")),
        )

    return states


def _incident_to_item(incident: Any, request_id: str) -> dict[str, Any]:
    now = _now_iso()
    incident_id = _deterministic_incident_id(
        incident.accession_number,
        incident.rule_id,
        incident.details,
    )

    return {
        "incidentId": incident_id,
        "accessionNumber": incident.accession_number,
        "ruleId": incident.rule_id,
        "severity": incident.severity,
        "status": "OPEN",
        "title": incident.title,
        "description": incident.description,
        "recommendedAction": incident.recommended_action,
        "details": incident.details,
        "createdAt": now,
        "lastEvaluatedAt": now,
        "sourceRequestId": request_id,
    }


def _store_incident(item: dict[str, Any]) -> None:
    incidents_table.update_item(
        Key={"incidentId": item["incidentId"]},
        UpdateExpression=(
            "SET accessionNumber = :accession_number, "
            "ruleId = :rule_id, "
            "severity = :severity, "
            "#status = if_not_exists(#status, :status), "
            "title = :title, "
            "description = :description, "
            "recommendedAction = :recommended_action, "
            "details = :details, "
            "createdAt = if_not_exists(createdAt, :created_at), "
            "lastEvaluatedAt = :last_evaluated_at, "
            "sourceRequestId = :source_request_id"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":accession_number": item["accessionNumber"],
            ":rule_id": item["ruleId"],
            ":severity": item["severity"],
            ":status": item["status"],
            ":title": item["title"],
            ":description": item["description"],
            ":recommended_action": item["recommendedAction"],
            ":details": item["details"],
            ":created_at": item["createdAt"],
            ":last_evaluated_at": item["lastEvaluatedAt"],
            ":source_request_id": item["sourceRequestId"],
        },
    )


def _publish_alert(item: dict[str, Any]) -> None:
    sns_client.publish(
        TopicArn=ALERT_TOPIC_ARN,
        Subject=f"{item['severity']} imaging reconciliation incident",
        Message=json.dumps(
            {
                "incidentId": item["incidentId"],
                "accessionNumber": item["accessionNumber"],
                "ruleId": item["ruleId"],
                "severity": item["severity"],
                "title": item["title"],
                "recommendedAction": item["recommendedAction"],
            },
            indent=2,
        ),
    )


def _deterministic_incident_id(
    accession_number: str,
    rule_id: str,
    details: dict[str, Any],
) -> str:
    fingerprint = json.dumps(details, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{accession_number}|{rule_id}|{fingerprint}".encode("utf-8"))
    return f"inc-{digest.hexdigest()[:16]}"


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
