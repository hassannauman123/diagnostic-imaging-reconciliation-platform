variable "aws_region" {
  description = "AWS region for Phase 3 resources."
  type        = string
  default     = "ca-central-1"
}

variable "environment" {
  description = "Environment name used in resource names."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Short project name used in resource names."
  type        = string
  default     = "di-recon-platform"
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the ingest Lambda."
  type        = number
  default     = 7
}

variable "raw_event_retention_days" {
  description = "Number of days before raw sample events expire from S3."
  type        = number
  default     = 30
}

variable "ingest_lambda_reserved_concurrency" {
  description = "Maximum concurrent executions allowed for the ingest Lambda."
  type        = number
  default     = 2
}

variable "api_throttle_burst_limit" {
  description = "Short burst request limit for the HTTP API default stage."
  type        = number
  default     = 5
}

variable "api_throttle_rate_limit" {
  description = "Steady-state requests per second limit for the HTTP API default stage."
  type        = number
  default     = 2
}
