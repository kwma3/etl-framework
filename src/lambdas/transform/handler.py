import json
import os
from datetime import datetime, timezone
import boto3

def get_boto_client(service_name):
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url and os.environ.get("LOCALSTACK_HOSTNAME"):
        endpoint_url = f"http://{os.environ['LOCALSTACK_HOSTNAME']}:{os.environ.get('EDGE_PORT', '4566')}"
    return boto3.client(service_name, endpoint_url=endpoint_url)

s3_client = get_boto_client("s3")
dynamodb_client = get_boto_client("dynamodb")

PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET")
METADATA_TABLE = os.environ.get("METADATA_TABLE")

def lambda_handler(event, context):
    print("Received transform event:", json.dumps(event))

    job_id = event["job_id"]
    timestamp = event["timestamp"]
    raw_bucket = event["raw_bucket"]
    raw_key = event["raw_key"]

    # Read raw data from S3
    response = s3_client.get_object(Bucket=raw_bucket, Key=raw_key)
    raw_payload = json.loads(response["Body"].read().decode("utf-8"))
    records = raw_payload.get("records", [])

    transformed_records = []
    filtered_records = []

    for item in records:
        try:
            amount = float(item.get("amount", 0))
            email = str(item.get("email", "")).strip().lower()
            currency = str(item.get("currency", "USD")).strip().upper()

            # Simple validation rules: amount must be > 0 and email contains '@'
            if amount > 0 and "@" in email:
                transformed_records.append({
                    "id": item.get("id"),
                    "name": item.get("name", "").strip(),
                    "email": email,
                    "amount": round(amount, 2),
                    "currency": currency,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
            else:
                filtered_records.append({
                    "record": item,
                    "reason": "Invalid amount or email format"
                })
        except Exception as e:
            filtered_records.append({
                "record": item,
                "reason": str(e)
            })

    processed_key = f"processed/{job_id}/transformed_data.json"

    # Store transformed data in Processed S3 Bucket
    s3_client.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=processed_key,
        Body=json.dumps({
            "job_id": job_id,
            "transformed_at": datetime.now(timezone.utc).isoformat(),
            "valid_count": len(transformed_records),
            "invalid_count": len(filtered_records),
            "records": transformed_records,
            "dropped": filtered_records
        }),
        ContentType="application/json"
    )

    # Update DynamoDB Status
    dynamodb_client.update_item(
        TableName=METADATA_TABLE,
        Key={
            "job_id": {"S": job_id},
            "timestamp": {"S": timestamp}
        },
        UpdateExpression="SET #s = :status, processed_s3_key = :key, valid_count = :valid, filtered_count = :filtered, updated_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": {"S": "TRANSFORMED"},
            ":key": {"S": processed_key},
            ":valid": {"N": str(len(transformed_records))},
            ":filtered": {"N": str(len(filtered_records))},
            ":now": {"S": datetime.now(timezone.utc).isoformat()}
        }
    )

    return {
        "statusCode": 200,
        "job_id": job_id,
        "timestamp": timestamp,
        "processed_bucket": PROCESSED_BUCKET,
        "processed_key": processed_key,
        "valid_count": len(transformed_records),
        "filtered_count": len(filtered_records)
    }
