# Phase 4 AWS Processing and DynamoDB

## Goal

Phase 4 consumes normalized events from the SQS processing queue and stores operational state in DynamoDB.

This phase proves that the platform can move beyond ingestion and maintain cloud-backed state by accession number and source system.

## What Terraform Adds

Terraform in `infra/phase3/` now also creates:

- Processor Lambda
- SQS event source mapping from the processing queue to the processor Lambda
- DynamoDB `ExamSystemState` table
- DynamoDB `EventHistory` table
- CloudWatch log group for the processor Lambda
- IAM role and least-needed policy for SQS reads and DynamoDB writes

This phase still does not create Step Functions, incident storage, SNS alerts, Cognito, or a dashboard. Those are later phases.

## Architecture

```text
API Gateway POST /events
        |
        v
Ingest Lambda
        |
        | valid normalized event
        v
SQS processing queue
        |
        v
Processor Lambda
        |
        +--> DynamoDB ExamSystemState
        |    latest state by accessionNumber + sourceSystem
        |
        +--> DynamoDB EventHistory
             event history by accessionNumber + timestamp#eventId
```

Invalid messages still go to the failed-events queue from Phase 3.

## DynamoDB Tables

### ExamSystemState

Purpose: stores the latest known state for each accession number and source system.

Primary key:

```text
PK: accessionNumber
SK: sourceSystem
```

Example lookup:

```text
ACC-10001 + RIS
ACC-10001 + PACS
ACC-10001 + POWERSCRIBE
```

This table gives the reconciliation layer a fast way to compare what each system currently believes about the same exam.

### EventHistory

Purpose: stores every normalized event processed for an accession number.

Primary key:

```text
PK: accessionNumber
SK: timestamp#eventId
```

This table supports investigation and replay-style thinking. A support analyst can see how the accession state changed over time.

## Deploy

From the Phase 3/4 Terraform folder:

```bash
cd infra/phase3
terraform init
terraform plan
terraform apply
```

Expected new resources include:

- `aws_dynamodb_table.exam_system_state`
- `aws_dynamodb_table.event_history`
- `aws_lambda_function.processor`
- `aws_lambda_event_source_mapping.processing_queue_to_processor`

## Test

Set the endpoint from the project root:

```bash
export EVENTS_ENDPOINT="$(terraform -chdir=infra/phase3 output -raw events_endpoint)"
```

Post a valid event:

```bash
curl -X POST "$EVENTS_ENDPOINT" \
  -H "Content-Type: application/json" \
  --data @samples/ris-order-created.json
```

Expected response:

```json
{
  "message": "Event accepted",
  "eventId": "evt-ris-001",
  "accessionNumber": "ACC-10001",
  "rawS3Key": "raw-events/2026/05/21/evt-ris-001.json"
}
```

Then confirm the processor ran:

```bash
aws logs tail /aws/lambda/di-recon-platform-dev-processor --since 5m
```

Expected log message:

```text
event_processed
```

Check latest state:

```bash
aws dynamodb get-item \
  --table-name "$(terraform -chdir=infra/phase3 output -raw exam_system_state_table_name)" \
  --key '{"accessionNumber":{"S":"ACC-10001"},"sourceSystem":{"S":"RIS"}}'
```

Check event history:

```bash
aws dynamodb query \
  --table-name "$(terraform -chdir=infra/phase3 output -raw event_history_table_name)" \
  --key-condition-expression "accessionNumber = :accession" \
  --expression-attribute-values '{":accession":{"S":"ACC-10001"}}'
```

## AWS Console Locations

Processor Lambda:

```text
Lambda > Functions > di-recon-platform-dev-processor
```

DynamoDB tables:

```text
DynamoDB > Tables > di-recon-platform-dev-exam-system-state
DynamoDB > Tables > di-recon-platform-dev-event-history
```

Processor logs:

```text
CloudWatch > Log groups > /aws/lambda/di-recon-platform-dev-processor
```

Processing queue:

```text
SQS > Queues > di-recon-platform-dev-processing
```

## Why This Phase Matters

Phase 3 proved cloud ingestion. Phase 4 proves asynchronous cloud processing and durable state.

This is the point where the project starts looking like a real platform workflow:

- API Gateway handles external ingestion.
- SQS buffers work.
- Lambda processes messages independently.
- DynamoDB keeps current state and history.
- CloudWatch provides processing visibility.

The next phase uses this stored state to run reconciliation rules in AWS.
