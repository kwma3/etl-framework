import json
import os
from datetime import datetime, timezone
import boto3

def get_boto_client(service_name):
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url and os.environ.get("LOCALSTACK_HOSTNAME"):
        endpoint_url = f"http://{os.environ['LOCALSTACK_HOSTNAME']}:{os.environ.get('EDGE_PORT', '4566')}"
    return boto3.client(service_name, endpoint_url=endpoint_url)

dynamodb_client = get_boto_client("dynamodb")
events_client = get_boto_client("events")

METADATA_TABLE = os.environ.get("METADATA_TABLE")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

def lambda_handler(event, context):
    print("Received load event:", json.dumps(event))

    job_id = event["job_id"]
    timestamp = event["timestamp"]
    processed_key = event["processed_key"]
    valid_count = event.get("valid_count", 0)
    filtered_count = event.get("filtered_count", 0)

    completed_at = datetime.now(timezone.utc).isoformat()

    # Mark Job as COMPLETED in DynamoDB
    dynamodb_client.update_item(
        TableName=METADATA_TABLE,
        Key={
            "job_id": {"S": job_id},
            "timestamp": {"S": timestamp}
        },
        UpdateExpression="SET #s = :status, completed_at = :completed_at, updated_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": {"S": "COMPLETED"},
            ":completed_at": {"S": completed_at},
            ":now": {"S": completed_at}
        }
    )

    # Publish notification event to EventBridge
    try:
        events_client.put_events(
            Entries=[
                {
                    "Source": "etl.framework",
                    "DetailType": "ETLJobCompleted",
                    "Detail": json.dumps({
                        "job_id": job_id,
                        "processed_key": processed_key,
                        "valid_count": valid_count,
                        "filtered_count": filtered_count,
                        "completed_at": completed_at
                    }),
                    "EventBusName": EVENT_BUS_NAME
                }
            ]
        )
    except Exception as e:
        print(f"Warning: Failed to publish completion event to EventBridge: {e}")

    return {
        "statusCode": 200,
        "job_id": job_id,
        "status": "COMPLETED",
        "valid_count": valid_count,
        "filtered_count": filtered_count,
        "completed_at": completed_at
    }
