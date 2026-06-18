data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  name_prefix                 = "${var.project_name}-${var.environment}"
  bucket_name                 = lower("${local.name_prefix}-raw-${data.aws_caller_identity.current.account_id}-${var.aws_region}")
  lambda_reserved_concurrency = var.ingest_lambda_reserved_concurrency >= 0 ? var.ingest_lambda_reserved_concurrency : null
}

resource "aws_s3_bucket" "raw_events" {
  bucket = local.bucket_name

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_s3_bucket_public_access_block" "raw_events" {
  bucket = aws_s3_bucket.raw_events.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_events" {
  bucket = aws_s3_bucket.raw_events.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_events" {
  bucket = aws_s3_bucket.raw_events.id

  rule {
    id     = "expire-raw-synthetic-events"
    status = "Enabled"

    filter {
      prefix = "raw-events/"
    }

    expiration {
      days = var.raw_event_retention_days
    }
  }
}

resource "aws_sqs_queue" "failed_events" {
  name                      = "${local.name_prefix}-failed-events"
  message_retention_seconds = 1209600

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_sqs_queue" "processing" {
  name                       = "${local.name_prefix}-processing"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.failed_events.arn
    maxReceiveCount     = 3
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

data "archive_file" "ingest_lambda" {
  type        = "zip"
  output_path = "${path.module}/ingest_lambda.zip"

  source {
    filename = "handler.py"
    content  = file("${path.module}/../../src/aws/ingest_lambda/handler.py")
  }

  source {
    filename = "shared/__init__.py"
    content  = file("${path.module}/../../src/shared/__init__.py")
  }

  source {
    filename = "shared/models.py"
    content  = file("${path.module}/../../src/shared/models.py")
  }

  source {
    filename = "shared/normalizer.py"
    content  = file("${path.module}/../../src/shared/normalizer.py")
  }

  source {
    filename = "shared/validator.py"
    content  = file("${path.module}/../../src/shared/validator.py")
  }
}

data "archive_file" "processor_lambda" {
  type        = "zip"
  output_path = "${path.module}/processor_lambda.zip"

  source {
    filename = "handler.py"
    content  = file("${path.module}/../../src/aws/processor_lambda/handler.py")
  }
}

resource "aws_iam_role" "ingest_lambda" {
  name = "${local.name_prefix}-ingest-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ingest_lambda" {
  name = "${local.name_prefix}-ingest-lambda-policy"
  role = aws_iam_role.ingest_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.ingest_lambda.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.raw_events.arn}/raw-events/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.processing.arn,
          aws_sqs_queue.failed_events.arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "ingest_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-ingest"
  retention_in_days = var.log_retention_days

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_lambda_function" "ingest" {
  function_name                  = "${local.name_prefix}-ingest"
  role                           = aws_iam_role.ingest_lambda.arn
  handler                        = "handler.lambda_handler"
  runtime                        = "python3.11"
  filename                       = data.archive_file.ingest_lambda.output_path
  source_code_hash               = data.archive_file.ingest_lambda.output_base64sha256
  timeout                        = 10
  memory_size                    = 128
  reserved_concurrent_executions = local.lambda_reserved_concurrency

  environment {
    variables = {
      RAW_BUCKET              = aws_s3_bucket.raw_events.bucket
      PROCESSING_QUEUE_URL    = aws_sqs_queue.processing.url
      FAILED_EVENTS_QUEUE_URL = aws_sqs_queue.failed_events.url
      ENVIRONMENT             = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy.ingest_lambda,
    aws_cloudwatch_log_group.ingest_lambda
  ]

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_apigatewayv2_api" "ingestion" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type"]
    allow_methods = ["POST", "OPTIONS"]
    allow_origins = ["*"]
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_apigatewayv2_integration" "ingest_lambda" {
  api_id                 = aws_apigatewayv2_api.ingestion.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_events" {
  api_id    = aws_apigatewayv2_api.ingestion.id
  route_key = "POST /events"
  target    = "integrations/${aws_apigatewayv2_integration.ingest_lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.ingestion.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.api_throttle_burst_limit
    throttling_rate_limit  = var.api_throttle_rate_limit
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "3"
  }
}

resource "aws_dynamodb_table" "exam_system_state" {
  name         = "${local.name_prefix}-exam-system-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "accessionNumber"
  range_key    = "sourceSystem"

  attribute {
    name = "accessionNumber"
    type = "S"
  }

  attribute {
    name = "sourceSystem"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "4"
  }
}

resource "aws_dynamodb_table" "event_history" {
  name         = "${local.name_prefix}-event-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "accessionNumber"
  range_key    = "eventKey"

  attribute {
    name = "accessionNumber"
    type = "S"
  }

  attribute {
    name = "eventKey"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "4"
  }
}

resource "aws_iam_role" "processor_lambda" {
  name = "${local.name_prefix}-processor-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "processor_lambda" {
  name = "${local.name_prefix}-processor-lambda-policy"
  role = aws_iam_role.processor_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.processor_lambda.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = aws_sqs_queue.processing.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.exam_system_state.arn,
          aws_dynamodb_table.event_history.arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "processor_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-processor"
  retention_in_days = var.log_retention_days

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "4"
  }
}

resource "aws_lambda_function" "processor" {
  function_name    = "${local.name_prefix}-processor"
  role             = aws_iam_role.processor_lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.processor_lambda.output_path
  source_code_hash = data.archive_file.processor_lambda.output_base64sha256
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      STATE_TABLE_NAME         = aws_dynamodb_table.exam_system_state.name
      EVENT_HISTORY_TABLE_NAME = aws_dynamodb_table.event_history.name
      ENVIRONMENT              = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy.processor_lambda,
    aws_cloudwatch_log_group.processor_lambda
  ]

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Phase       = "4"
  }
}

resource "aws_lambda_event_source_mapping" "processing_queue_to_processor" {
  event_source_arn        = aws_sqs_queue.processing.arn
  function_name           = aws_lambda_function.processor.arn
  batch_size              = 5
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ingestion.execution_arn}/*/*"
}
