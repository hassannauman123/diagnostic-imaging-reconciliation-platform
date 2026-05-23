# Dashboard Requirements

## Dashboard Goal

Give support analysts one operational view of accession state, incidents, event history, and failed messages.

## Pages

### 1. Overview

Cards:

- Events received today
- Open incidents
- High severity incidents
- DLQ messages
- Missing acknowledgements
- Last event received time

### 2. Accession Search

Search by accession number.

Example: `ACC-10001`

Display side-by-side state across systems:

| Field | RIS | PACS | Reporting | Downstream |
|---|---|---|---|---|
| Exam Description | CT Head Without Contrast | CT Head Without Contrast | Blank | N/A |
| Exam Status | Pending | Images Available | In Progress | N/A |
| Report Status | Pending | N/A | Final | N/A |
| Patient Name | SYNTHETIC^JANE_UPDATED | SYNTHETIC^JANE | SYNTHETIC^JANE | N/A |
| ACK | N/A | N/A | N/A | Missing |

### 3. Incidents

Display:

- severity
- accession number
- rule ID
- title
- status
- created timestamp
- recommended action

### 4. Event History

For each accession number, display:

- timestamp
- event ID
- source system
- message type
- processing result
- raw message reference

### 5. Failed Messages / DLQ

Display:

- failed event ID
- failure reason
- source system
- timestamp
- raw message path
- retry/reprocess option as future enhancement
