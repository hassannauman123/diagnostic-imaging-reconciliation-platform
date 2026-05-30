from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3

from shared.normalizer import normalize_event
from shared.validator import validate_event


s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

RAW_BUCKET = os.environ["RAW_BUCKET"]
PROCESSING_QUEUE_URL = os.environ["PROCESSING_QUEUE_URL"]
FAILED_EVENTS_QUEUE_URL = os.environ["FAILED_EVENTS_QUEUE_URL"]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", "unknown")
    print(json.dumps({"message": "ingest_request_received", "requestId": request_id}))

    payload, parse_error = _parse_api_gateway_body(event)
    if parse_error:
        _send_failed_event(
            payload={"rawBody": event.get("body")},
            errors=[parse_error],
            request_id=request_id,
        )
        return _response(400, {"message": "Invalid JSON payload", "errors": [parse_error]})

    validation = validate_event(payload)
    if not validation.is_valid:
        _send_failed_event(payload=payload, errors=validation.errors, request_id=request_id)
        print(
            json.dumps(
                {
                    "message": "validation_failed",
                    "requestId": request_id,
                    "eventId": payload.get("eventId", "UNKNOWN"),
                    "errors": validation.errors,
                }
            )
        )
        return _response(400, {"message": "Validation failed", "errors": validation.errors})

    raw_s3_key = _archive_raw_event(payload)
    normalized_event = normalize_event(payload)
    normalized_message = {
        "eventId": normalized_event.event_id,
        "sourceSystem": normalized_event.source_system,
        "messageType": normalized_event.message_type,
        "timestamp": normalized_event.timestamp_iso,
        "accessionNumber": normalized_event.accession_number,
        "patient": normalized_event.patient,
        "exam": normalized_event.exam,
        "report": normalized_event.report,
        "ack": normalized_event.ack,
        "rawS3Bucket": RAW_BUCKET,
        "rawS3Key": raw_s3_key,
    }

    sqs_client.send_message(
        QueueUrl=PROCESSING_QUEUE_URL,
        MessageBody=json.dumps(normalized_message),
    )

    print(
        json.dumps(
            {
                "message": "event_accepted",
                "requestId": request_id,
                "eventId": normalized_event.event_id,
                "accessionNumber": normalized_event.accession_number,
                "rawS3Key": raw_s3_key,
            }
        )
    )

    return _response(
        202,
        {
            "message": "Event accepted",
            "eventId": normalized_event.event_id,
            "accessionNumber": normalized_event.accession_number,
            "rawS3Key": raw_s3_key,
        },
    )


def _parse_api_gateway_body(event: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    body = event.get("body")
    if not body:
        return {}, "Request body is required"

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        return {}, f"Malformed JSON: {exc.msg}"

    if not isinstance(parsed, dict):
        return {}, "JSON payload must be an object"

    return parsed, None


def _archive_raw_event(payload: dict[str, Any]) -> str:
    event_id = str(payload.get("eventId", "unknown-event"))
    timestamp = str(payload.get("timestamp", _now_iso()))
    dt = _parse_timestamp_or_now(timestamp)
    key = (
        "raw-events/"
        f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/"
        f"{event_id}.json"
    )

    s3_client.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(payload, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def _send_failed_event(payload: dict[str, Any], errors: list[str], request_id: str) -> None:
    failed_message = {
        "requestId": request_id,
        "eventId": payload.get("eventId", "UNKNOWN"),
        "sourceSystem": payload.get("sourceSystem", "UNKNOWN"),
        "messageType": payload.get("messageType", "UNKNOWN"),
        "errors": errors,
        "payload": payload,
        "failedAt": _now_iso(),
    }
    sqs_client.send_message(
        QueueUrl=FAILED_EVENTS_QUEUE_URL,
        MessageBody=json.dumps(failed_message),
    )


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_timestamp_or_now(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

