# Phase 1 Local Reconciliation Engine

## Goal

Phase 1 proves the core diagnostic imaging reconciliation logic locally before introducing AWS services.

The engine uses synthetic JSON files from `samples/`, validates them, normalizes them into a common internal shape, builds current accession state in memory, applies reconciliation rules, and prints incidents with recommended support actions.

No AWS SDK, database, queue, dashboard, or real healthcare data is used in this phase.

## How to Run

Run from the project root:

```bash
python src/local/run_demo.py
```

## How the Local Engine Works

1. `src/local/run_demo.py` loads every JSON file from `samples/`.
2. `src/shared/validator.py` checks required fields:
   - `eventId`
   - `sourceSystem`
   - `messageType`
   - `timestamp`
   - `accessionNumber`
3. Invalid messages are reported as validation failures.
4. `src/shared/normalizer.py` maps valid source payloads into a `NormalizedEvent`.
5. `src/shared/state_store.py` keeps the latest state per accession number and source system in memory.
6. `src/shared/rules.py` evaluates reconciliation rules against the current state.
7. `src/shared/incident_builder.py` creates incident records with rule ID, severity, details, and recommended action.

## Implemented Rules

### RULE_001_BLANK_EXAM_DESCRIPTION

Detects when RIS has a non-empty exam description but PowerScribe/reporting has a blank exam description.

Severity: `MEDIUM`

### RULE_002_FINAL_REPORT_MISMATCH

Detects when PowerScribe/reporting has `reportStatus = FINAL`, but RIS is not `FINAL`, `COMPLETE`, `COMPLETED`, or `REPORTED`.

Severity: `HIGH`

### RULE_003_STALE_PATIENT_DEMOGRAPHICS

Detects when RIS has newer or different patient demographics than PACS or PowerScribe/reporting for the same accession number.

Severity: `HIGH`

### RULE_004_MISSING_DOWNSTREAM_ACK

Detects when a downstream acknowledgement was expected but not received.

Severity: `MEDIUM`

### RULE_005_CONFLICTING_ACCESSION_STATE

Implemented for cancelled RIS states that conflict with active imaging/reporting state. The current Phase 1 sample set does not trigger this rule because it is focused on the four primary demo incidents.

Severity: `CRITICAL`

### RULE_006_INVALID_MESSAGE

Handled by validation. The intentionally bad sample event fails because it is missing `accessionNumber`.

## Expected Demo Result

The current sample set produces:

- `7` events loaded
- `6` events processed
- `1` validation failure
- `4` incidents created
- `1` failed event

Expected incidents:

- `MEDIUM` - blank exam description in PowerScribe while RIS has valid exam description
- `HIGH` - PowerScribe report is final but RIS is still pending or incomplete
- `HIGH` - patient demographics are stale across systems
- `MEDIUM` - downstream acknowledgement missing

## Why Local Before AWS

The reconciliation rules are the business logic. Building them locally first keeps the project explainable and testable before adding cloud infrastructure.

This phase separates the workflow problem from AWS implementation details. Later phases can reuse the same validation, normalization, state, and rule concepts behind API Gateway, Lambda, SQS, DynamoDB, Step Functions, and CloudWatch.
