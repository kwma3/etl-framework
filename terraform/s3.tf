resource "aws_s3_bucket" "raw_data" {
  bucket        = "${var.project_name}-raw-${var.environment}"
  force_destroy = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Layer       = "Raw"
  }
}

resource "aws_s3_bucket" "processed_data" {
  bucket        = "${var.project_name}-processed-${var.environment}"
  force_destroy = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Layer       = "Processed"
  }
}
