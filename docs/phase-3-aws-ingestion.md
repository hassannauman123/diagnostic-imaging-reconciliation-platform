# Phase 3 AWS Ingestion Layer

## Goal

Phase 3 moves event ingestion into AWS while keeping reconciliation, DynamoDB state, Step Functions, and the dashboard out of scope for now.

This phase proves that AWS can receive synthetic diagnostic imaging events, validate them, archive the raw message, normalize valid messages, queue valid events for later processing, and preserve invalid messages for investigation.

## What Terraform Creates

Terraform in `infra/phase3/` creates:

- API Gateway HTTP API with `POST /events`
- Python ingest Lambda
- S3 bucket for raw event archive
- SQS processing queue for normalized valid events
- SQS failed-events queue for validation failures and future DLQ use
- CloudWatch log group with short retention
- IAM role and least-needed policy for the Lambda

It does not create EC2, NAT Gateway, VPC, RDS, DynamoDB, Step Functions, SNS, Cognito, or a dashboard.

## Architecture

```text
curl / synthetic sender
        |
        v
API Gateway POST /events
        |
        v
Ingest Lambda
        |
        | valid event
        | - archive raw JSON to S3
        | - normalize event
        | - send normalized event to SQS
        v
S3 raw archive + SQS processing queue

Invalid event
        |
        v
Ingest Lambda validation failure
        |
        v
SQS failed-events queue + HTTP 400 response
```

## Prerequisites

Check your tools:

```bash
aws --version
terraform version
```

Configure your AWS credentials if you have not already:

```bash
aws configure
```

Recommended region:

```text
ca-central-1
```

Confirm the terminal is authenticated:

```bash
aws sts get-caller-identity
```

## Cost Controls

Phase 3 is designed to stay low cost:

- no EC2
- no NAT Gateway
- no VPC
- no provisioned Lambda concurrency
- no DynamoDB yet
- CloudWatch logs retained for 7 days by default
- raw S3 sample events expire after 30 days by default
- Lambda runs only when called
- API Gateway throttling limits request bursts
- Lambda reserved concurrency is disabled by default for low-quota accounts, but can be enabled with a Terraform variable after a quota increase

Create an AWS Budget alert before deploying if this is your first AWS hands-on project.

Recommended budget:

```text
Monthly budget: $5 or $10
Alerts: 50%, 80%, 100%
```

See `docs/phase-3-cost-guardrails.md` for a cost-focused diagram and resource-by-resource cost notes.

## Deploy

Run Terraform from the Phase 3 folder, not the empty top-level `infra/` folder:

```bash
cd infra/phase3
terraform init
terraform plan
terraform apply
```

Type `yes` when Terraform asks for apply confirmation.

After apply, Terraform prints outputs including:

```text
events_endpoint
raw_events_bucket
processing_queue_url
failed_events_queue_url
ingest_lambda_name
```

## Test Valid Event

From the project root, set the endpoint:

```bash
export EVENTS_ENDPOINT="$(terraform -chdir=infra/phase3 output -raw events_endpoint)"
```

Post a valid RIS event:

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

Then check:

- S3 bucket contains the raw JSON file
- SQS processing queue contains one normalized message
- CloudWatch Logs for the ingest Lambda show `event_accepted`

## Test Invalid Event

Post the intentionally bad event:

```bash
curl -X POST "$EVENTS_ENDPOINT" \
  -H "Content-Type: application/json" \
  --data @samples/bad-message-missing-accession.json
```

Expected response:

```json
{
  "message": "Validation failed",
  "errors": ["Missing required field: accessionNumber"]
}
```

Then check:

- SQS failed-events queue contains the failed event details
- CloudWatch Logs show `validation_failed`

## Useful AWS CLI Checks

Read Terraform outputs:

```bash
terraform -chdir=infra/phase3 output
```

List raw S3 archive objects:

```bash
aws s3 ls "s3://$(terraform -chdir=infra/phase3 output -raw raw_events_bucket)" --recursive
```

Peek at the processing queue:

```bash
aws sqs receive-message \
  --queue-url "$(terraform -chdir=infra/phase3 output -raw processing_queue_url)" \
  --max-number-of-messages 1
```

Peek at the failed-events queue:

```bash
aws sqs receive-message \
  --queue-url "$(terraform -chdir=infra/phase3 output -raw failed_events_queue_url)" \
  --max-number-of-messages 1
```

## Clean Up

When you are done testing, destroy the resources:

```bash
terraform -chdir=infra/phase3 destroy
```

Type `yes`.

This is the most important cost-control command. It removes the AWS resources Terraform created for Phase 3.

## Why This Phase Matters

Phase 1 proved the rules locally. Phase 2 exposed the logic through a local API. Phase 3 starts the cloud-native architecture by replacing local ingestion with managed AWS ingestion.

The important platform-engineering pattern is decoupling:

```text
API Gateway receives quickly.
Lambda validates and normalizes.
S3 preserves the raw event.
SQS buffers work for future processing.
Failed messages are kept for investigation.
```

The system is not reconciling inside AWS yet. That starts in later phases after DynamoDB and processing Lambda are added.
