#!/usr/bin/env python3
import json
import os
import sys
import time
import uuid
import boto3

ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_client(service):
    return boto3.client(
        service,
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

def main():
    print(f"Connecting to LocalStack at {ENDPOINT_URL}...")
    sfn_client = get_client("stepfunctions")
    dynamodb_client = get_client("dynamodb")
    s3_client = get_client("s3")
    events_client = get_client("events")

    # Discover state machine ARN
    state_machines = sfn_client.list_state_machines().get("stateMachines", [])
    etl_sm = next((sm for sm in state_machines if "etl-framework-pipeline" in sm["name"]), None)

    if not etl_sm:
        print("Error: Could not find ETL state machine in LocalStack. Did you run terraform apply?")
        sys.exit(1)

    sm_arn = etl_sm["stateMachineArn"]
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    payload = {
        "job_id": job_id,
        "records": [
            {"id": "rec_101", "name": "Jane Doe", "email": "JANE@EXAMPLE.COM", "amount": "349.99", "currency": "usd"},
            {"id": "rec_102", "name": "Mark Spencer", "email": "mark.spencer@corp.net", "amount": "1250.00", "currency": "eur"},
            {"id": "rec_103", "name": "Corrupt Entry", "email": "invalid_email_format", "amount": "-50.00", "currency": "usd"}
        ]
    }

    print(f"\n[1/4] Triggering Step Functions State Machine...")
    print(f"State Machine ARN: {sm_arn}")
    print(f"Job ID: {job_id}")

    execution = sfn_client.start_execution(
        stateMachineArn=sm_arn,
        name=f"exec-{job_id}",
        input=json.dumps(payload)
    )

    execution_arn = execution["executionArn"]
    print(f"Execution started: {execution_arn}")

    print("\n[2/4] Polling execution status...")
    status = "RUNNING"
    for _ in range(30):
        desc = sfn_client.describe_execution(executionArn=execution_arn)
        status = desc["status"]
        if status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
            break
        time.sleep(1)

    print(f"Execution finished with status: {status}")
    if status != "SUCCEEDED":
        print(f"Execution details: {json.dumps(desc, indent=2, default=str)}")
        sys.exit(1)

    output = json.loads(desc.get("output", "{}"))
    print("\n[3/4] Step Function Execution Output:")
    print(json.dumps(output, indent=2))

    print("\n[4/4] Verifying DynamoDB Tracking Table:")
    table_name = "etl-framework-metadata-dev"
    try:
        ddb_res = dynamodb_client.query(
            TableName=table_name,
            KeyConditionExpression="job_id = :jid",
            ExpressionAttributeValues={":jid": {"S": job_id}}
        )
        items = ddb_res.get("Items", [])
        if items:
            print("Found record in DynamoDB:")
            print(json.dumps(items[0], indent=2))
        else:
            print("Warning: Job record not found in DynamoDB.")
    except Exception as e:
        print(f"Could not query DynamoDB: {e}")

    # Inspect processed S3 file
    try:
        processed_bucket = "etl-framework-processed-dev"
        processed_key = f"processed/{job_id}/transformed_data.json"
        s3_obj = s3_client.get_object(Bucket=processed_bucket, Key=processed_key)
        content = json.loads(s3_obj["Body"].read().decode("utf-8"))
        print(f"\nSuccessfully verified transformed data in S3 (s3://{processed_bucket}/{processed_key}):")
        print(json.dumps(content, indent=2))
    except Exception as e:
        print(f"Note: S3 check error: {e}")

if __name__ == "__main__":
    main()
