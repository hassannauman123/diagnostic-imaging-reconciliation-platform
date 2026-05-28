# Cloud-Native Diagnostic Imaging Reconciliation Platform

A healthcare-inspired AWS project that simulates diagnostic imaging workflow mismatches across systems such as RIS, PACS, reporting/PowerScribe-style platforms, and downstream consumers.

The project uses **synthetic data only**. It does not use real PHI, workplace screenshots, real logs, real server names, credentials, or internal documentation.

## Problem

In diagnostic imaging environments, multiple systems may disagree about the state of the same exam. For example:

- RIS has the correct exam description, but the reporting system has a blank exam description.
- Reporting says the report is final, but RIS still shows pending or incomplete.
- Patient demographics are updated in one system but stale in another.
- A message fails processing and lands in a failed queue.
- A downstream system does not acknowledge a message.
- The same accession number has conflicting state across systems.

Support analysts often need to manually check multiple systems, logs, queues, messages, and downstream statuses to understand what broke.

## Solution

This platform ingests synthetic diagnostic imaging events, archives raw messages, normalizes system-specific payloads, tracks current state by accession number, runs reconciliation rules, creates incidents, and alerts support users when systems disagree.

## Planned AWS Architecture

- API Gateway for event ingestion
- Lambda for validation, normalization, processing, and reconciliation logic
- SQS for asynchronous processing
- SQS dead-letter queue for failed events
- DynamoDB for current exam state, event history, and incidents
- S3 for raw message archive and replay/audit history
- Step Functions for reconciliation workflow orchestration
- CloudWatch for logs, metrics, dashboards, and alarms
- SNS for alert notifications
- Cognito for protected admin dashboard access
- Terraform for infrastructure as code
- GitHub Actions for CI/CD
- AWS Budgets for cost controls

## MVP Scope

The first version will prove the core workflow:

1. Send synthetic RIS/PowerScribe/PACS/downstream events.
2. Store raw messages.
3. Normalize events into a common model.
4. Update current state by accession number.
5. Detect mismatches using reconciliation rules.
6. Create incidents.
7. Show issues in a simple dashboard.
8. Demonstrate failure handling with a dead-letter queue.

## Sample Scenarios

The `samples/` folder contains synthetic event payloads for:

- RIS order created
- PACS images available
- PowerScribe/reporting receives blank exam description
- PowerScribe/reporting final report event
- RIS patient demographic update
- Downstream acknowledgement missing
- Invalid message missing accession number

## Phase 1 Local Demo

Phase 1 builds the reconciliation logic locally before adding AWS infrastructure.

Run from the project root:

```bash
python src/local/run_demo.py
```

The local demo proves that the project can:

- load synthetic JSON events from `samples/`
- validate required event fields
- reject an invalid message missing `accessionNumber`
- normalize valid events into a common model
- maintain current state by accession number and source system
- evaluate reconciliation rules without hardcoded incident output
- print operational incidents and recommended support actions

Example output:

```text
Diagnostic Imaging Reconciliation - Phase 1 Local Demo
==========================================================
Sample directory: samples

Events loaded: 7
Events processed: 6
Validation failures: 1
Incidents created: 4
Failed events: 1

Validation failures
-------------------
- evt-bad-001 (RIS ORDER_CREATED) from bad-message-missing-accession.json
  Reason: Missing required field: accessionNumber

Incidents
---------
- [MEDIUM] RULE_001_BLANK_EXAM_DESCRIPTION: Blank exam description in PowerScribe while RIS has valid exam description
- [HIGH] RULE_002_FINAL_REPORT_MISMATCH: PowerScribe report is final but RIS is still pending or incomplete
- [HIGH] RULE_003_STALE_PATIENT_DEMOGRAPHICS: Patient demographics are stale across systems
- [MEDIUM] RULE_004_MISSING_DOWNSTREAM_ACK: Downstream acknowledgement missing
```

## Phase 2 Local API

Phase 2 wraps the same reconciliation logic in a local FastAPI service.

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API from the project root:

```bash
uvicorn src.api.app:app --reload
```

Useful endpoints:

- `GET /health`
- `POST /events`
- `GET /accessions/{accessionNumber}`
- `GET /incidents`
- `GET /events/{accessionNumber}`
- `GET /failed-events`
- `POST /reset`

Example flow:

```bash
curl -X POST http://127.0.0.1:8000/reset

curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  --data @samples/ris-order-created.json

curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  --data @samples/powerscribe-report-started-blank-description.json

curl http://127.0.0.1:8000/incidents
```

The interactive API docs are available at:

```text
http://127.0.0.1:8000/docs
```

## Privacy and Compliance Boundary

This is a portfolio and learning project. It is healthcare-inspired, not a production healthcare system.

The project intentionally uses synthetic data only. It does not claim PHIA, HIPAA, SOC 2, or production compliance. The design discusses privacy-aware patterns such as audit history, access control, and synthetic data boundaries without claiming real compliance certification.

## Project Roadmap

### Phase 0: Foundation

- Define problem statement
- Define personas
- Document before/after workflow
- Add architecture diagrams
- Add sample synthetic events
- Define data model
- Define reconciliation rules
- Document privacy boundaries

### Phase 1: Local Reconciliation Engine

- Load synthetic JSON messages
- Validate required fields
- Normalize events
- Store current state in memory
- Apply reconciliation rules
- Print incidents locally

### Phase 2: Local API

- Add API endpoints for event ingestion, accession lookup, incidents, and health checks

### Phase 3: AWS Ingestion

- Deploy API Gateway, Lambda, S3, SQS, and DLQ

### Phase 4: AWS Processing

- Add processor Lambda and DynamoDB state/event history tables

### Phase 5: Reconciliation Workflow

- Add Step Functions, incidents table, and SNS alerts

### Phase 6: Dashboard

- Add operational dashboard for accession search, incidents, event history, and failed messages

### Phase 7: Observability

- Add CloudWatch custom metrics, alarms, dashboards, and operational runbook notes

### Phase 8: Terraform and CI/CD

- Make infrastructure repeatable and deployment-ready

### Phase 9: Portfolio Polish

- Add screenshots, demo video, LinkedIn post, architecture write-up, and resume bullets

## Status

Current phase: **Phase 2 local API complete**.

Next planned phase: **Phase 3 AWS ingestion layer**, after explicit approval.
