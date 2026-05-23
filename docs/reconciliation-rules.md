# Reconciliation Rules

## RULE_001_BLANK_EXAM_DESCRIPTION

### Purpose

Detect when RIS has a valid exam description but the reporting system has a blank exam description.

### Trigger Condition

- RIS `exam.examDescription` is not empty
- Reporting or PowerScribe `exam.examDescription` is empty, null, or missing

### Severity

MEDIUM

### Example

RIS:

```json
"examDescription": "CT Head Without Contrast"
```

Reporting:

```json
"examDescription": ""
```

### Recommended Support Action

Check whether the exam description/order update message was mapped correctly and whether the reporting system needs a corrected resend.

---

## RULE_002_FINAL_REPORT_MISMATCH

### Purpose

Detect when the reporting system says a report is final but RIS does not show the exam/report as complete.

### Trigger Condition

- Reporting `reportStatus` equals `FINAL`
- RIS `examStatus` is not one of `FINAL`, `COMPLETE`, or `REPORTED`

### Severity

HIGH

### Recommended Support Action

Check whether the final report outbound/update message reached RIS and whether a queue or interface issue blocked the status update.

---

## RULE_003_STALE_PATIENT_DEMOGRAPHICS

### Purpose

Detect when patient demographics are newer in RIS but stale in PACS or reporting.

### Trigger Condition

- RIS patient name, DOB, or patient ID differs from another system for the same accession number
- RIS event timestamp is newer than the downstream system state timestamp

### Severity

HIGH

### Recommended Support Action

Check patient update propagation, downstream demographic synchronization, and whether a resend/reconciliation action is required.

---

## RULE_004_MISSING_DOWNSTREAM_ACK

### Purpose

Detect when a downstream system was expected to acknowledge a message but did not.

### Trigger Condition

- `ack.expected` is true
- `ack.received` is false

### Severity

MEDIUM

### Recommended Support Action

Check downstream system availability, interface queue status, and whether the message should be retried or replayed.

---

## RULE_005_CONFLICTING_ACCESSION_STATE

### Purpose

Detect incompatible state across systems for the same accession number.

### Trigger Condition

Examples:

- RIS says `CANCELLED`, but PACS says `IMAGES_AVAILABLE`
- RIS says `PENDING`, but reporting says `FINAL`
- PACS has images but RIS has no matching active order state

### Severity

CRITICAL

### Recommended Support Action

Review accession mapping, order status, image state, and reporting state to determine which system is authoritative.

---

## RULE_006_INVALID_MESSAGE

### Purpose

Detect messages that cannot be safely processed due to missing required fields.

### Required Fields

- `eventId`
- `sourceSystem`
- `messageType`
- `timestamp`
- `accessionNumber`

### Severity

LOW by default. Can be HIGH depending on message type.

### Recommended Support Action

Review validation error, raw payload, and upstream sender mapping. Move the failed message to DLQ or failed-message storage for investigation.
