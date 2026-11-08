# Package Framework & Jobs into a single Lambda zip
data "archive_file" "etl_dispatcher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/.build/etl_dispatcher.zip"
  excludes    = ["lambdas"]
}

# Unified Task Dispatcher Lambda Function
resource "aws_lambda_function" "etl_dispatcher" {
  filename         = data.archive_file.etl_dispatcher_zip.output_path
  source_code_hash = data.archive_file.etl_dispatcher_zip.output_base64sha256
  function_name    = "${var.project_name}-dispatcher-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_dispatcher.lambda_handler"
  runtime          = "python3.11"
  timeout          = 120

  environment {
    variables = {
      RAW_BUCKET       = aws_s3_bucket.raw_data.bucket
      PROCESSED_BUCKET = aws_s3_bucket.processed_data.bucket
      METADATA_TABLE   = aws_dynamodb_table.etl_metadata.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Role        = "TaskDispatcher"
  }
}
