resource "aws_sfn_state_machine" "etl_pipeline" {
  name     = "${var.project_name}-pipeline-${var.environment}"
  role_arn = aws_iam_role.sfn_exec.arn

  definition = jsonencode({
    Comment = "Serverless ETL Orchestration Pipeline"
    StartAt = "ExtractStep"
    States = {
      ExtractStep = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = aws_lambda_function.extract.arn
          "Payload.$"    = "$"
        }
        ResultSelector = {
          "statusCode.$"   = "$.Payload.statusCode"
          "job_id.$"       = "$.Payload.job_id"
          "timestamp.$"    = "$.Payload.timestamp"
          "raw_bucket.$"   = "$.Payload.raw_bucket"
          "raw_key.$"      = "$.Payload.raw_key"
          "record_count.$" = "$.Payload.record_count"
        }
        Next = "TransformStep"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
      }
      TransformStep = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = aws_lambda_function.transform.arn
          "Payload.$"    = "$"
        }
        ResultSelector = {
          "statusCode.$"       = "$.Payload.statusCode"
          "job_id.$"           = "$.Payload.job_id"
          "timestamp.$"        = "$.Payload.timestamp"
          "processed_bucket.$" = "$.Payload.processed_bucket"
          "processed_key.$"    = "$.Payload.processed_key"
          "valid_count.$"      = "$.Payload.valid_count"
          "filtered_count.$"   = "$.Payload.filtered_count"
        }
        Next = "LoadStep"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 2
            BackoffRate     = 2.0
          }
        ]
      }
      LoadStep = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          "FunctionName" = aws_lambda_function.load.arn
          "Payload.$"    = "$"
        }
        ResultSelector = {
          "statusCode.$"     = "$.Payload.statusCode"
          "job_id.$"         = "$.Payload.job_id"
          "status.$"         = "$.Payload.status"
          "valid_count.$"    = "$.Payload.valid_count"
          "filtered_count.$" = "$.Payload.filtered_count"
          "completed_at.$"   = "$.Payload.completed_at"
        }
        End = true
      }
    }
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
