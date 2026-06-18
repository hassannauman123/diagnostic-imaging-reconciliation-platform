output "api_base_url" {
  description = "Base URL for the Phase 3 ingestion API."
  value       = aws_apigatewayv2_api.ingestion.api_endpoint
}

output "events_endpoint" {
  description = "POST endpoint for synthetic event ingestion."
  value       = "${aws_apigatewayv2_api.ingestion.api_endpoint}/events"
}

output "raw_events_bucket" {
  description = "S3 bucket used to archive raw incoming messages."
  value       = aws_s3_bucket.raw_events.bucket
}

output "processing_queue_url" {
  description = "SQS queue URL for normalized valid events."
  value       = aws_sqs_queue.processing.url
}

output "failed_events_queue_url" {
  description = "SQS queue URL for invalid or failed ingestion events."
  value       = aws_sqs_queue.failed_events.url
}

output "ingest_lambda_name" {
  description = "Name of the ingest Lambda function."
  value       = aws_lambda_function.ingest.function_name
}

output "processor_lambda_name" {
  description = "Name of the Phase 4 processor Lambda function."
  value       = aws_lambda_function.processor.function_name
}

output "exam_system_state_table_name" {
  description = "DynamoDB table storing latest state by accession number and source system."
  value       = aws_dynamodb_table.exam_system_state.name
}

output "event_history_table_name" {
  description = "DynamoDB table storing normalized event history by accession number."
  value       = aws_dynamodb_table.event_history.name
}

output "reconciliation_incidents_table_name" {
  description = "DynamoDB table storing reconciliation incidents."
  value       = aws_dynamodb_table.reconciliation_incidents.name
}

output "reconciliation_lambda_name" {
  description = "Name of the Phase 5 reconciliation Lambda function."
  value       = aws_lambda_function.reconciliation.function_name
}

output "reconciliation_state_machine_arn" {
  description = "Step Functions state machine ARN for accession reconciliation."
  value       = aws_sfn_state_machine.reconciliation.arn
}

output "reconciliation_alerts_topic_arn" {
  description = "SNS topic ARN for high-severity reconciliation alerts."
  value       = aws_sns_topic.reconciliation_alerts.arn
}
