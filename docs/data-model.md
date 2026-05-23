# Data Model

## DynamoDB Table: ExamSystemState

Stores the latest known state of each accession number per source system.

### Primary Key

```text
PK: accessionNumber
SK: sourceSystem
```

### Example Item

```json
{
  "accessionNumber": "ACC-10001",
  "sourceSystem": "POWERSCRIBE",
  "patientId": "PAT-9001",
  "patientName": "SYNTHETIC^JANE",
  "dateOfBirth": "1980-01-01",
  "examDescription": "",
  "examStatus": "IN_PROGRESS",
  "reportStatus": "FINAL",
  "messageType": "REPORT_FINAL",
  "lastUpdated": "2026-05-21T15:45:00Z",
  "sourceEventId": "evt-ps-002"
}
```

## DynamoDB Table: EventHistory

Stores normalized event history for each accession number.

### Primary Key

```text
PK: accessionNumber
SK: eventTimestamp#eventId
```

### Example Item

```json
{
  "accessionNumber": "ACC-10001",
  "eventKey": "2026-05-21T15:45:00Z#evt-ps-002",
  "eventId": "evt-ps-002",
  "sourceSystem": "POWERSCRIBE",
  "messageType": "REPORT_FINAL",
  "rawS3Path": "s3://di-recon-raw/dev/2026/05/21/evt-ps-002.json",
  "normalizedPayload": {
    "reportStatus": "FINAL"
  }
}
```

## DynamoDB Table: ReconciliationIncidents

Stores detected mismatches and recommended actions.

### Primary Key

```text
PK: incidentId
```

### GSI

```text
GSI1PK: accessionNumber
GSI1SK: createdAt
```

### Example Item

```json
{
  "incidentId": "inc-0001",
  "accessionNumber": "ACC-10001",
  "severity": "HIGH",
  "status": "OPEN",
  "ruleId": "RULE_002_FINAL_REPORT_MISMATCH",
  "title": "Reporting system final but RIS still pending",
  "details": {
    "risExamStatus": "PENDING",
    "reportingReportStatus": "FINAL"
  },
  "recommendedAction": "Check whether the final report update reached RIS or failed in an interface queue.",
  "createdAt": "2026-05-21T15:46:00Z"
}
```
