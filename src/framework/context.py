import os
import json
from typing import Any, Dict, Optional
import boto3

class ETLContext:
    """Carries execution state, parameters, and helper methods across tasks."""

    def __init__(
        self,
        job_id: str,
        job_name: str,
        task_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        endpoint_url: Optional[str] = None
    ):
        self.job_id = job_id
        self.job_name = job_name
        self.task_name = task_name
        self.parameters = parameters or {}
        self.state = state or {}
        self.metrics: Dict[str, Any] = {}

        # Resolve LocalStack / AWS endpoint
        if not endpoint_url:
            endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
            if not endpoint_url and os.environ.get("LOCALSTACK_HOSTNAME"):
                endpoint_url = f"http://{os.environ['LOCALSTACK_HOSTNAME']}:{os.environ.get('EDGE_PORT', '4566')}"

        self.endpoint_url = endpoint_url
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.raw_bucket = os.environ.get("RAW_BUCKET", "etl-framework-raw-dev")
        self.processed_bucket = os.environ.get("PROCESSED_BUCKET", "etl-framework-processed-dev")
        self.metadata_table = os.environ.get("METADATA_TABLE", "etl-framework-metadata-dev")

        # Initialize boto3 clients
        self.s3_client = boto3.client("s3", endpoint_url=self.endpoint_url, region_name=self.region)
        self.dynamodb_client = boto3.client("dynamodb", endpoint_url=self.endpoint_url, region_name=self.region)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a value from the shared inter-task state."""
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the shared inter-task state."""
        self.state[key] = value

    def record_metric(self, metric_name: str, value: Any) -> None:
        """Records a metric for auditing in DynamoDB."""
        self.metrics[metric_name] = value

    def save_s3(self, key: str, data: Any, bucket_type: str = "raw") -> str:
        """Serializes and saves data to S3."""
        bucket = self.raw_bucket if bucket_type == "raw" else self.processed_bucket
        body = json.dumps(data, default=str)
        self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json"
        )
        return f"s3://{bucket}/{key}"

    def read_s3(self, key: str, bucket_type: str = "raw") -> Any:
        """Reads and deserializes JSON data from S3."""
        bucket = self.raw_bucket if bucket_type == "raw" else self.processed_bucket
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
