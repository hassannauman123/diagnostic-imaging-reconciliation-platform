# Phase 5 AWS Reconciliation Workflow

## Goal

Phase 5 runs reconciliation rules inside AWS after events have been ingested, normalized, queued, processed, and stored in DynamoDB.

This phase proves the platform can compare current state across systems for one accession number, create incident records, and publish high-severity alerts.

## What Terraform Adds

Terraform in `infra/phase3/` now also creates:

- Step Functions reconciliation state machine
- Reconciliation Lambda
- DynamoDB `ReconciliationIncidents` table
- SNS topic for high-severity reconciliation alerts
- CloudWatch log group for the reconciliation Lambda
- IAM roles and least-needed policies for Step Functions, Lambda, DynamoDB, and SNS

This phase still does not create Cognito, a dashboard, CloudWatch dashboards, CloudWatch alarms, or GitHub Actions.

## Architecture

```text
API Gateway POST /events
        |
        v
Ingest Lambda
        |
        v
SQS processing queue
        |
        v
Processor Lambda
        |
        +--> DynamoDB ExamSystemState
        +--> DynamoDB EventHistory
        |
        v
Step Functions reconciliation workflow
        |
        v
Reconciliation Lambda
        |
        +--> read ExamSystemState
        +--> apply reconciliation rules
        +--> write ReconciliationIncidents
        +--> publish HIGH/CRITICAL incidents to SNS
```

## How It Works

1. The ingest Lambda receives a synthetic event and sends a normalized message to SQS.
2. The processor Lambda consumes the SQS message.
3. The processor Lambda updates latest state and event history in DynamoDB.
4. The processor Lambda starts the Step Functions reconciliation workflow with the accession number.
5. Step Functions invokes the reconciliation Lambda.
6. The reconciliation Lambda loads all current system states for that accession.
7. The shared reconciliation rules evaluate the accession state.
8. Incidents are written to DynamoDB.
9. `HIGH` and `CRITICAL` incidents are published to SNS.

## DynamoDB Table

### ReconciliationIncidents

Purpose: stores detected system mismatches and recommended support action.

Primary key:

```text
PK: incidentId
```

GSI:

```text
accessionNumber-createdAt-index
PK: accessionNumber
SK: createdAt
```

The incident ID is deterministic from accession number, rule ID, and rule details. That keeps repeated reconciliation runs from creating endless duplicate incidents for the same mismatch.

## Deploy

From the Terraform folder:

```bash
cd infra/phase3
terraform plan
terraform apply
```

Expected new resources include:

- `aws_sfn_state_machine.reconciliation`
- `aws_lambda_function.reconciliation`
- `aws_dynamodb_table.reconciliation_incidents`
- `aws_sns_topic.reconciliation_alerts`

## Cost Notes

Phase 5 is still designed for cautious testing:

- Step Functions Standard charges per state transition.
- DynamoDB incidents table uses on-demand billing.
- SNS topic exists, but no subscription is created by default.
- Lambda only runs when events are processed.
- CloudWatch log retention remains short.

For learning/testing, send a small number of sample events and destroy the stack when you are done experimenting.

## Test

Send a RIS order event:

```bash
export EVENTS_ENDPOINT="$(terraform -chdir=infra/phase3 output -raw events_endpoint)"

curl -X POST "$EVENTS_ENDPOINT" \
  -H "Content-Type: application/json" \
  --data @samples/ris-order-created.json
```

Send a PowerScribe blank-description event:

```bash
curl -X POST "$EVENTS_ENDPOINT" \
  -H "Content-Type: application/json" \
  --data @samples/powerscribe-report-started-blank-description.json
```

Expected result:

- Processor Lambda writes RIS and PowerScribe state to DynamoDB.
- Step Functions runs after each processed event.
- Reconciliation Lambda detects `RULE_001_BLANK_EXAM_DESCRIPTION`.
- DynamoDB `ReconciliationIncidents` contains a `MEDIUM` incident.

Send the final report event:

```bash
curl -X POST "$EVENTS_ENDPOINT" \
  -H "Content-Type: application/json" \
  --data @samples/powerscribe-report-final.json
```

Expected result:

- Reconciliation Lambda detects `RULE_002_FINAL_REPORT_MISMATCH`.
- DynamoDB `ReconciliationIncidents` contains a `HIGH` incident.
- SNS publish is attempted for the high-severity incident.

## Useful AWS CLI Checks

List recent Step Functions executions:

```bash
aws stepfunctions list-executions \
  --state-machine-arn "$(terraform -chdir=infra/phase3 output -raw reconciliation_state_machine_arn)" \
  --max-results 5
```

Tail reconciliation Lambda logs:

```bash
aws logs tail /aws/lambda/di-recon-platform-dev-reconciliation --since 10m
```

Query incidents for an accession:

```bash
aws dynamodb query \
  --table-name "$(terraform -chdir=infra/phase3 output -raw reconciliation_incidents_table_name)" \
  --index-name accessionNumber-createdAt-index \
  --key-condition-expression "accessionNumber = :accession" \
  --expression-attribute-values '{":accession":{"S":"ACC-10001"}}'
```

## AWS Console Locations

Step Functions workflow:

```text
Step Functions > State machines > di-recon-platform-dev-reconciliation
```

Reconciliation Lambda:

```text
Lambda > Functions > di-recon-platform-dev-reconciliation
```

Incident table:

```text
DynamoDB > Tables > di-recon-platform-dev-reconciliation-incidents
```

SNS topic:

```text
SNS > Topics > di-recon-platform-dev-reconciliation-alerts
```

Reconciliation logs:

```text
CloudWatch > Log groups > /aws/lambda/di-recon-platform-dev-reconciliation
```

## Why This Phase Matters

Phase 5 is where the project becomes a true reconciliation platform instead of only an ingestion and storage pipeline.

The important architecture pattern is separation of responsibility:

- Processor Lambda updates durable operational state.
- Step Functions makes the reconciliation workflow visible and inspectable.
- Reconciliation Lambda applies business rules.
- DynamoDB stores incidents for later dashboard/API use.
- SNS creates an alert path for high-severity issues.

This gives you a clear architecture story for platform engineering and solutions architecture conversations.
