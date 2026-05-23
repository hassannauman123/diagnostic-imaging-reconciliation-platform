# Demo Story

## 60-Second Demo Narrative

In diagnostic imaging, the hard support issues are not always full outages. Sometimes the issue is that multiple systems disagree about the same exam.

For example, RIS may have the correct exam description, while the reporting system displays a blank exam description. Or the reporting system may say the report is final, while RIS still shows the exam as pending.

This project simulates those problems using synthetic data only.

The platform receives fake RIS, PACS, reporting, and downstream events through an API. It stores the raw message for audit history, normalizes the event, processes it asynchronously, updates current state by accession number, and runs reconciliation rules.

When systems disagree, the platform creates an incident, sends an alert, and exposes the issue in an operational dashboard.

The goal is not just to use AWS services. The goal is to model a real operational problem and show how cloud architecture can reduce manual investigation time, improve visibility, and make failure handling easier.

## Demo Scenarios

### Scenario 1: Blank Exam Description

1. Send RIS order event with valid exam description.
2. Send reporting event with blank exam description.
3. System creates medium-severity incident.

### Scenario 2: Final Report Mismatch

1. Send reporting final event.
2. RIS still has pending status.
3. System creates high-severity incident.

### Scenario 3: Stale Demographics

1. Send RIS patient update.
2. PACS/reporting still has old patient name.
3. System creates high-severity incident.

### Scenario 4: Missing ACK

1. Send downstream ACK event where expected is true and received is false.
2. System creates medium-severity incident.

### Scenario 5: Invalid Message

1. Send message missing accession number.
2. System sends it to failed handling/DLQ flow.
