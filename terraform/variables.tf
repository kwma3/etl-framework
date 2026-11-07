variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localhost:4566"
}

variable "project_name" {
  description = "Project identifier prefix"
  type        = string
  default     = "etl-framework"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}
