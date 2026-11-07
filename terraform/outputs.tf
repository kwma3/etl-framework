output "raw_bucket_name" {
  description = "Name of the raw S3 bucket"
  value       = aws_s3_bucket.raw_data.bucket
}

output "processed_bucket_name" {
  description = "Name of the processed S3 bucket"
  value       = aws_s3_bucket.processed_data.bucket
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB ETL metadata table"
  value       = aws_dynamodb_table.etl_metadata.name
}

output "step_function_arn" {
  description = "ARN of the Step Functions ETL State Machine"
  value       = aws_sfn_state_machine.etl_pipeline.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge trigger rule"
  value       = aws_cloudwatch_event_rule.etl_trigger_rule.name
}

output "lambda_extract_name" {
  value = aws_lambda_function.extract.function_name
}

output "lambda_transform_name" {
  value = aws_lambda_function.transform.function_name
}

output "lambda_load_name" {
  value = aws_lambda_function.load.function_name
}
