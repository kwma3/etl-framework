resource "aws_sfn_state_machine" "etl_pipeline" {
  name     = "${var.project_name}-pipeline-${var.environment}"
  role_arn = aws_iam_role.sfn_exec.arn

  definition = templatefile("${path.module}/asl/etl_pipeline.asl.json", {
    lambda_arn = aws_lambda_function.etl_dispatcher.arn
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
