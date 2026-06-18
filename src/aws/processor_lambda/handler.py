from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError


dynamodb = boto3.resource("dynamodb")
sfn_client = boto3.client("stepfunctions")

STATE_TABLE_NAME = os.environ["STATE_TABLE_NAME"]
EVENT_HISTORY_TABLE_NAME = os.environ["EVENT_HISTORY_TABLE_NAME"]
RECONCILIATION_STATE_MACHINE_ARN = os.environ["RECONCILIATION_STATE_MACHINE_ARN"]

state_table = dynamodb.Table(STATE_TABLE_NAME)
event_history_table = dynamodb.Table(EVENT_HISTORY_TABLE_NAME)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    request_id = getattr(context, "aws_request_id", "unknown")
    records = event.get("Records", [])
    batch_failures: list[dict[str, str]] = []

    print(
        json.dumps(
            {
                "message": "processor_batch_received",
                "requestId": request_id,
                "recordCount": len(records),
            }
        )
    )

    for record in records:
        message_id = record.get("messageId", "unknown")

        try:
            normalized_event = _parse_sqs_record(record)
            state_updated = _write_current_state(normalized_event)
            _write_event_history(normalized_event)
            reconciliation_execution_arn = _start_reconciliation_workflow(
                normalized_event,
                request_id,
            )

            print(
                json.dumps(
                    {
                        "message": "event_processed",
                        "requestId": request_id,
                        "messageId": message_id,
                        "eventId": normalized_event["eventId"],
                        "accessionNumber": normalized_event["accessionNumber"],
                        "sourceSystem": normalized_event["sourceSystem"],
                        "stateUpdated": state_updated,
                        "reconciliationExecutionArn": reconciliation_execution_arn,
                    }
                )
            )
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "message": "event_processing_failed",
                        "requestId": request_id,
                        "messageId": message_id,
                        "error": str(exc),
                    }
                )
            )
            batch_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_failures}


def _parse_sqs_record(record: dict[str, Any]) -> dict[str, Any]:
    body = record.get("body")
    if not body:
        raise ValueError("SQS record body is required")

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("SQS message body must be a JSON object")

    required_fields = [
        "eventId",
        "sourceSystem",
        "messageType",
        "timestamp",
        "accessionNumber",
    ]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        raise ValueError(f"Normalized event missing required fields: {', '.join(missing_fields)}")

    return payload


def _write_current_state(event: dict[str, Any]) -> bool:
    state_item = {
        "accessionNumber": event["accessionNumber"],
        "sourceSystem": event["sourceSystem"],
        "messageType": event["messageType"],
        "lastUpdated": event["timestamp"],
        "sourceEventId": event["eventId"],
        "patient": _dict_or_empty(event.get("patient")),
        "exam": _dict_or_empty(event.get("exam")),
        "report": _dict_or_empty(event.get("report")),
        "ack": _dict_or_empty(event.get("ack")),
        "rawS3Bucket": event.get("rawS3Bucket", ""),
        "rawS3Key": event.get("rawS3Key", ""),
        "updatedAt": _now_iso(),
    }

    try:
        state_table.put_item(
            Item=state_item,
            ConditionExpression="attribute_not_exists(lastUpdated) OR lastUpdated <= :incoming_timestamp",
            ExpressionAttributeValues={":incoming_timestamp": event["timestamp"]},
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise


def _write_event_history(event: dict[str, Any]) -> None:
    event_history_table.put_item(
        Item={
            "accessionNumber": event["accessionNumber"],
            "eventKey": f"{event['timestamp']}#{event['eventId']}",
            "eventId": event["eventId"],
            "sourceSystem": event["sourceSystem"],
            "messageType": event["messageType"],
            "timestamp": event["timestamp"],
            "patient": _dict_or_empty(event.get("patient")),
            "exam": _dict_or_empty(event.get("exam")),
            "report": _dict_or_empty(event.get("report")),
            "ack": _dict_or_empty(event.get("ack")),
            "rawS3Bucket": event.get("rawS3Bucket", ""),
            "rawS3Key": event.get("rawS3Key", ""),
            "processedAt": _now_iso(),
        }
    )


def _start_reconciliation_workflow(event: dict[str, Any], request_id: str) -> str:
    response = sfn_client.start_execution(
        stateMachineArn=RECONCILIATION_STATE_MACHINE_ARN,
        input=json.dumps(
            {
                "accessionNumber": event["accessionNumber"],
                "triggeringEventId": event["eventId"],
                "triggeringSourceSystem": event["sourceSystem"],
                "processorRequestId": request_id,
            }
        ),
    )
    return str(response["executionArn"])


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
