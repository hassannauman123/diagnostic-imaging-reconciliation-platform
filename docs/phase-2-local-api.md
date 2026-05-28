# Phase 2 Local API

## Goal

Phase 2 wraps the Phase 1 reconciliation engine in a local HTTP API. It is still local-only and does not use AWS.

The API receives synthetic RIS, PACS, PowerScribe/reporting, and downstream events one at a time. It reuses the shared validation, normalization, in-memory state store, and reconciliation rules from Phase 1.

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API from the project root:

```bash
uvicorn src.api.app:app --reload
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### GET /health

Returns a simple health check.

### POST /events

Accepts one synthetic event payload. Valid events are normalized, added to in-memory state, and reconciled.

Invalid events return `400` with validation errors.

### GET /accessions/{accessionNumber}

Returns the latest known state for each source system for one accession number, plus currently detected incidents for that accession.

### GET /incidents

Returns the current reconciliation incidents.

### GET /events/{accessionNumber}

Returns normalized event history for one accession number.

### GET /failed-events

Returns validation failures captured during local API usage.

### POST /reset

Clears in-memory state and validation failures.

## Demo Commands

Start with a clean state:

```bash
curl -X POST http://127.0.0.1:8000/reset
```

Post a RIS order:

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  --data @samples/ris-order-created.json
```

Post a PowerScribe event with a blank exam description:

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  --data @samples/powerscribe-report-started-blank-description.json
```

View incidents:

```bash
curl http://127.0.0.1:8000/incidents
```

Post the intentionally invalid message:

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  --data @samples/bad-message-missing-accession.json
```

View failed events:

```bash
curl http://127.0.0.1:8000/failed-events
```

## Why This Phase Matters

Phase 1 proved the reconciliation logic with a local script. Phase 2 turns that logic into a service interface.

This prepares the project for AWS because API Gateway and Lambda will eventually receive events in a similar request/response pattern, while SQS and DynamoDB will replace local in-memory processing and storage.
