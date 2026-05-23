# Before and After Workflow

## Before

A user reports an issue such as:

> The report is final in the reporting system, but RIS still shows the exam as pending.

The support analyst may need to manually check:

1. RIS exam status
2. PACS image status
3. Reporting system status
4. message logs
5. failed queues
6. downstream acknowledgements
7. patient demographics
8. accession number consistency

This workflow is slow because the analyst has to mentally reconstruct the event timeline from multiple systems.

## After

The platform receives synthetic events from each system and tracks the current state by accession number.

The analyst searches for an accession number and sees:

| Field | RIS | PACS | Reporting | Downstream |
|---|---|---|---|---|
| Exam Description | CT Head Without Contrast | CT Head Without Contrast | Blank | N/A |
| Exam Status | Pending | Images Available | In Progress | N/A |
| Report Status | Pending | N/A | Final | N/A |
| Patient Name | SYNTHETIC^JANE_UPDATED | SYNTHETIC^JANE | SYNTHETIC^JANE | N/A |
| ACK | N/A | N/A | N/A | Missing |

The platform creates incidents:

- Blank exam description in reporting system
- Reporting final but RIS still pending
- Stale patient demographics
- Missing downstream acknowledgement

## Result

The analyst gets one operational view instead of manually checking multiple systems.

The value is not just technical automation. The value is faster triage, clearer incident context, and better support visibility.
