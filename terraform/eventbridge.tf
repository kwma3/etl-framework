# EventBridge Rule triggered by event pattern
resource "aws_cloudwatch_event_rule" "etl_trigger_rule" {
  name        = "${var.project_name}-trigger-rule-${var.environment}"
  description = "Trigger ETL pipeline via EventBridge event"

  event_pattern = jsonencode({
    "source"      = ["etl.trigger"]
    "detail-type" = ["StartETLJob"]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Target: Step Functions State Machine
resource "aws_cloudwatch_event_target" "step_functions_target" {
  rule      = aws_cloudwatch_event_rule.etl_trigger_rule.name
  target_id = "TriggerStepFunctionsETL"
  arn       = aws_sfn_state_machine.etl_pipeline.arn
  role_arn  = aws_iam_role.eventbridge_sfn_role.arn

  input_transformer {
    input_paths = {
      job_id  = "$.detail.job_id"
      records = "$.detail.records"
    }
    input_template = jsonencode({
      "job_id"  = "<job_id>"
      "records" = "<records>"
    })
  }
}
