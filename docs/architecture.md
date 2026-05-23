# Architecture

## Main README Architecture Diagram

```mermaid
flowchart TB
    subgraph Sources["Synthetic Healthcare-Inspired Sources"]
        RIS[RIS Event]
        PACS[PACS Event]
        PS[PowerScribe / Reporting Event]
        DS[Downstream ACK Event]
    end

    subgraph Ingestion["Ingestion Layer"]
        API[API Gateway<br/>POST /events]
        INGEST[Ingest Lambda<br/>Validate + Normalize]
    end

    subgraph Storage["Audit + Queue Layer"]
        S3[S3 Raw Message Archive]
        SQS[SQS Processing Queue]
        DLQ[SQS Dead-Letter Queue]
    end

    subgraph Processing["Processing Layer"]
        PROC[Processor Lambda]
        STATE[DynamoDB<br/>ExamSystemState]
        HISTORY[DynamoDB<br/>EventHistory]
    end

    subgraph Reconciliation["Reconciliation Layer"]
        SFN[Step Functions Workflow]
        RULES[Rules Lambda]
        INCIDENTS[DynamoDB<br/>ReconciliationIncidents]
    end

    subgraph Operations["Operations Layer"]
        CW[CloudWatch<br/>Logs / Metrics / Alarms]
        SNS[SNS Alerts]
        DASH[Admin Dashboard]
        COG[Cognito Auth]
    end

    RIS --> API
    PACS --> API
    PS --> API
    DS --> API

    API --> INGEST
    INGEST --> S3
    INGEST --> SQS

    SQS --> PROC
    SQS --> DLQ

    PROC --> STATE
    PROC --> HISTORY
    PROC --> SFN

    SFN --> RULES
    RULES --> INCIDENTS
    RULES --> SNS
    RULES --> CW

    COG --> DASH
    DASH --> STATE
    DASH --> HISTORY
    DASH --> INCIDENTS
    DASH --> DLQ
    DASH --> CW
```

## Executive Architecture Diagram

```mermaid
flowchart TB
    A[Diagnostic Imaging Systems<br/>Synthetic RIS / PACS / Reporting Events]
    A --> B[Cloud Ingestion Layer<br/>API Gateway + Lambda]
    B --> C[Raw Message Archive<br/>S3]
    B --> D[Event Processing Layer<br/>SQS + Lambda]
    D --> E[Operational State Store<br/>DynamoDB by Accession Number]
    D --> F[Reconciliation Engine<br/>Step Functions + Rules Lambda]
    F --> G[Incident Store<br/>DynamoDB]
    F --> H[Alerts<br/>SNS]
    F --> I[Observability<br/>CloudWatch Metrics, Logs, Alarms]
    E --> J[Admin Dashboard]
    G --> J
    I --> J
    J --> K[Support Analyst<br/>Single View of Mismatches]
```

## Event Ingestion Flow

```mermaid
sequenceDiagram
    participant Generator as Synthetic Event Generator
    participant API as API Gateway
    participant Ingest as Ingest Lambda
    participant S3 as S3 Raw Archive
    participant SQS as SQS Main Queue
    participant DLQ as Dead-Letter Queue

    Generator->>API: POST /events
    API->>Ingest: Forward event payload
    Ingest->>Ingest: Validate required fields

    alt Valid message
        Ingest->>S3: Store raw JSON message
        Ingest->>Ingest: Normalize event
        Ingest->>SQS: Send normalized event
        Ingest-->>API: 202 Accepted
        API-->>Generator: Event accepted
    else Invalid message
        Ingest->>DLQ: Send failed message
        Ingest-->>API: 400 Bad Request
        API-->>Generator: Validation failed
    end
```

## Message Processing Flow

```mermaid
sequenceDiagram
    participant SQS as SQS Main Queue
    participant Processor as Processor Lambda
    participant State as DynamoDB ExamSystemState
    participant History as DynamoDB EventHistory
    participant StepFn as Step Functions
    participant DLQ as Dead-Letter Queue

    SQS->>Processor: Deliver normalized event
    Processor->>Processor: Parse event

    alt Processing succeeds
        Processor->>State: Update latest system state
        Processor->>History: Write event history record
        Processor->>StepFn: Start reconciliation workflow
        Processor-->>SQS: Delete message from queue
    else Processing fails after retries
        SQS->>DLQ: Move message to DLQ
    end
```

## Reconciliation Workflow

```mermaid
flowchart TD
    A[Start Reconciliation<br/>Accession Number Received] --> B[Load Current State<br/>RIS / PACS / Reporting / Downstream]
    B --> C{RIS has exam description<br/>but reporting blank?}
    C -- Yes --> C1[Create Incident:<br/>Blank Exam Description]
    C -- No --> D
    C1 --> D{Reporting final<br/>but RIS not complete?}
    D -- Yes --> D1[Create Incident:<br/>Final Report Mismatch]
    D -- No --> E
    D1 --> E{Patient demographics stale<br/>across systems?}
    E -- Yes --> E1[Create Incident:<br/>Stale Demographics]
    E -- No --> F
    E1 --> F{Downstream ACK missing?}
    F -- Yes --> F1[Create Incident:<br/>Missing Acknowledgement]
    F -- No --> G
    F1 --> G{Conflicting accession state?}
    G -- Yes --> G1[Create Incident:<br/>Conflicting State]
    G -- No --> H[No New Incident]
    C1 --> I[Store Incident in DynamoDB]
    D1 --> I
    E1 --> I
    F1 --> I
    G1 --> I
    I --> J{Severity High or Critical?}
    J -- Yes --> K[Send SNS Alert]
    J -- No --> L[Log Only]
    K --> M[Emit CloudWatch Metric]
    L --> M
    H --> M
    M --> N[End]
```

## Dashboard User Flow

```mermaid
flowchart TD
    A[Support Analyst Opens Dashboard] --> B[Cognito Login]
    B --> C[Dashboard Home]
    C --> D[View Overview Metrics]
    C --> E[Search Accession Number]
    C --> F[View Open Incidents]
    C --> G[View Failed Messages / DLQ]
    E --> H[Load System State<br/>RIS / PACS / Reporting / Downstream]
    H --> I[Compare Fields Side-by-Side]
    I --> J{Mismatch Found?}
    J -- Yes --> K[Show Incident Details]
    J -- No --> L[Show Healthy State]
    K --> M[Show Event History]
    K --> N[Show Recommended Action]
    K --> O[Show Raw Message S3 Path]
```

## Failure Handling Flow

```mermaid
flowchart TD
    A[Incoming Event] --> B[Validate Payload]
    B --> C{Valid?}
    C -- No --> D[Reject Request or Send to DLQ]
    D --> E[Log Validation Error]
    E --> F[CloudWatch Metric:<br/>ValidationFailure]
    C -- Yes --> G[Send to SQS]
    G --> H[Processor Lambda]
    H --> I{Processing Successful?}
    I -- Yes --> J[Update DynamoDB]
    J --> K[Trigger Reconciliation]
    I -- No --> L[Retry Based on SQS Policy]
    L --> M{Retry Limit Reached?}
    M -- No --> H
    M -- Yes --> N[Move to DLQ]
    N --> O[CloudWatch Alarm]
    O --> P[SNS Alert]
    P --> Q[Dashboard Shows Failed Message]
```
