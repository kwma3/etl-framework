resource "aws_cloudwatch_dashboard" "etl_dashboard" {
  dashboard_name = "${var.project_name}-monitoring-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 3
        properties = {
          markdown = "## 📊 Serverless ETL Framework Monitoring Dashboard\n**Environment:** `${var.environment}` | **Pipeline:** `${aws_sfn_state_machine.etl_pipeline.name}` | **Dispatcher:** `${aws_lambda_function.etl_dispatcher.function_name}`\n\nMonitors Step Functions execution outcomes, Lambda task dispatcher latency/errors, and DynamoDB audit table activity."
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 3
        width  = 12
        height = 6
        properties = {
          title   = "Step Functions - Execution Status"
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          period  = 60
          stat    = "Sum"
          metrics = [
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { color = "#2ca02c" }],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { color = "#d62728" }],
            ["AWS/States", "ExecutionsTimedOut", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { color = "#ff7f0e" }],
            ["AWS/States", "ExecutionsAborted", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { color = "#7f7f7f" }],
            ["AWS/States", "ExecutionThrottled", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { color = "#9467bd" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 3
        width  = 12
        height = 6
        properties = {
          title  = "Step Functions - Pipeline Execution Duration (ms)"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Average", label = "Avg Duration (ms)" }],
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "p95", label = "p95 Duration (ms)" }],
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Maximum", label = "Max Duration (ms)" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 9
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Dispatcher - Invocations & Errors"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { color = "#1f77b4" }],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { color = "#d62728" }],
            ["AWS/Lambda", "Throttles", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { color = "#ff7f0e" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 9
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Dispatcher - Execution Latency (ms)"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { stat = "Average", label = "Avg Duration" }],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { stat = "p90", label = "p90 Duration" }],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { stat = "Maximum", label = "Max Duration" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 9
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Dispatcher - Concurrency"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          stat   = "Maximum"
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", aws_lambda_function.etl_dispatcher.function_name, { color = "#17becf" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 15
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB - Audit Table Consumed Capacity"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.etl_metadata.name, { color = "#2ca02c" }],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", aws_dynamodb_table.etl_metadata.name, { color = "#1f77b4" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 15
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB - Throttles & System Errors"
          view   = "timeSeries"
          region = var.aws_region
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/DynamoDB", "ThrottledRequests", "TableName", aws_dynamodb_table.etl_metadata.name, { color = "#ff7f0e" }],
            ["AWS/DynamoDB", "SystemErrors", "TableName", aws_dynamodb_table.etl_metadata.name, { color = "#d62728" }]
          ]
        }
      }
    ]
  })
}
