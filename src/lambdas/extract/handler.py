import json
import os
import uuid
from datetime import datetime, timezone
import boto3

def get_boto_client(service_name):
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url and os.environ.get("LOCALSTACK_HOSTNAME"):
        endpoint_url = f"http://{os.environ['LOCALSTACK_HOSTNAME']}:{os.environ.get('EDGE_PORT', '4566')}"
    return boto3.client(service_name, endpoint_url=endpoint_url)

s3_client = get_boto_client("s3")
dynamodb_client = get_boto_client("dynamodb")

RAW_BUCKET = os.environ.get("RAW_BUCKET")
METADATA_TABLE = os.environ.get("METADATA_TABLE")

def lambda_handler(event, context):
    print("Received extract event:", json.dumps(event))

    job_id = event.get("job_id", f"job-{uuid.uuid4().hex[:8]}")
    timestamp = datetime.now(timezone.utc).isoformat()

    # Incoming raw items or default sample batch
    records = event.get("records")
    if not records:
        records = [
            {"id": "usr_01", "name": "Alice Smith", "email": "ALICE@EXAMPLE.COM", "amount": "120.50", "currency": "usd"},
            {"id": "usr_02", "name": "Bob Jones", "email": "bob@example.com", "amount": "85.00", "currency": "eur"},
            {"id": "usr_03", "name": "Charlie Brown", "email": "CHARLIE@EXAMPLE.ORG", "amount": "250.75", "currency": "USD"},
            {"id": "usr_04", "name": "Invalid Row", "email": "not-an-email", "amount": "-10.00", "currency": "usd"}
        ]

    raw_key = f"raw/{job_id}/source_data.json"

    # Store raw data in S3
    s3_client.put_object(
        Bucket=RAW_BUCKET,
        Key=raw_key,
        Body=json.dumps({"job_id": job_id, "timestamp": timestamp, "records": records}),
        ContentType="application/json"
    )

    # Initialize DynamoDB Job Run Tracking
    dynamodb_client.put_item(
        TableName=METADATA_TABLE,
        Item={
            "job_id": {"S": job_id},
            "timestamp": {"S": timestamp},
            "status": {"S": "EXTRACTED"},
            "raw_s3_key": {"S": raw_key},
            "record_count": {"N": str(len(records))},
            "updated_at": {"S": timestamp}
        }
    )

    return {
        "statusCode": 200,
        "job_id": job_id,
        "timestamp": timestamp,
        "raw_bucket": RAW_BUCKET,
        "raw_key": raw_key,
        "record_count": len(records)
    }
