# Archive Lambda Code
data "archive_file" "extract_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambdas/extract"
  output_path = "${path.module}/.build/extract.zip"
}

data "archive_file" "transform_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambdas/transform"
  output_path = "${path.module}/.build/transform.zip"
}

data "archive_file" "load_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambdas/load"
  output_path = "${path.module}/.build/load.zip"
}

# Lambda: Extract
resource "aws_lambda_function" "extract" {
  filename         = data.archive_file.extract_zip.output_path
  source_code_hash = data.archive_file.extract_zip.output_base64sha256
  function_name    = "${var.project_name}-extract-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      RAW_BUCKET     = aws_s3_bucket.raw_data.bucket
      METADATA_TABLE = aws_dynamodb_table.etl_metadata.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Stage       = "Extract"
  }
}

# Lambda: Transform
resource "aws_lambda_function" "transform" {
  filename         = data.archive_file.transform_zip.output_path
  source_code_hash = data.archive_file.transform_zip.output_base64sha256
  function_name    = "${var.project_name}-transform-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      PROCESSED_BUCKET = aws_s3_bucket.processed_data.bucket
      METADATA_TABLE   = aws_dynamodb_table.etl_metadata.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Stage       = "Transform"
  }
}

# Lambda: Load & Notify
resource "aws_lambda_function" "load" {
  filename         = data.archive_file.load_zip.output_path
  source_code_hash = data.archive_file.load_zip.output_base64sha256
  function_name    = "${var.project_name}-load-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      METADATA_TABLE = aws_dynamodb_table.etl_metadata.name
      EVENT_BUS_NAME = "default"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Stage       = "Load"
  }
}
