# LinkedIn Post Copy

I built a serverless AWS event-processing platform inspired by diagnostic imaging workflows.

The scenario:
Multiple systems can disagree about the same exam. RIS, PACS, reporting systems, downstream systems, and acknowledgement workflows may each hold different state.

The platform:
Synthetic events are ingested through API Gateway, archived to S3, validated and normalized in Lambda, processed asynchronously with SQS, stored in DynamoDB, and reconciled through Step Functions.

If a mismatch is detected, such as a report being final in the reporting system while RIS still shows pending, the system creates an incident for human review.

AWS services used:
API Gateway, Lambda, SQS, S3, DynamoDB, Step Functions, SNS, CloudWatch, Terraform.

What I learned:
The biggest lessons were around event-driven design, failure handling, Terraform state, cost-conscious serverless architecture, and explaining architecture tradeoffs clearly.

This is a synthetic-data portfolio project only. No PHI, no real workplace data, no internal logs, and no production compliance claims.
