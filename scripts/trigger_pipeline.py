#!/usr/bin/env python3
import argparse
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
    parser = argparse.ArgumentParser(description="Trigger and observe Step Functions ETL Pipeline")
    parser.add_argument("--job", default="customer_orders", help="Name of registered ETL job to execute")
    parser.add_argument("--params", default="{}", help="JSON string of parameters for the job")
    parser.add_argument("--list", action="store_true", help="List registered jobs via Lambda dispatcher")
    args = parser.parse_args()

    lambda_client = get_client("lambda")
    sfn_client = get_client("stepfunctions")
    dynamodb_client = get_client("dynamodb")
    s3_client = get_client("s3")

    # Discover Dispatcher Lambda
    functions = lambda_client.list_functions().get("Functions", [])
    dispatcher_fn = next((f for f in functions if "dispatcher" in f["FunctionName"]), None)
    if not dispatcher_fn:
        print("Error: Could not find etl-framework-dispatcher Lambda. Run 'make deploy' first.")
        sys.exit(1)

    fn_name = dispatcher_fn["FunctionName"]

    # Handle --list action
    if args.list:
        res = lambda_client.invoke(
            FunctionName=fn_name,
            Payload=json.dumps({"action": "list_jobs"})
        )
        payload = json.loads(res["Payload"].read().decode("utf-8"))
        print("\nRegistered ETL Jobs:")
        print(json.dumps(payload.get("jobs", []), indent=2))
        return

    # Discover Step Functions State Machine
    state_machines = sfn_client.list_state_machines().get("stateMachines", [])
    etl_sm = next((sm for sm in state_machines if "etl-framework-pipeline" in sm["name"]), None)
    if not etl_sm:
        print("Error: Could not find ETL state machine in LocalStack. Run 'make deploy' first.")
        sys.exit(1)

    sm_arn = etl_sm["stateMachineArn"]
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    params = json.loads(args.params)

    input_payload = {
        "job_name": args.job,
        "job_id": job_id,
        "parameters": params,
        "context": {}
    }

    print(f"\n[1/4] Triggering Step Functions State Machine...")
    print(f"State Machine ARN: {sm_arn}")
    print(f"Job Name:          {args.job}")
    print(f"Job ID:            {job_id}")

    execution = sfn_client.start_execution(
        stateMachineArn=sm_arn,
        name=f"{args.job}-{job_id}",
        input=json.dumps(input_payload)
    )

    execution_arn = execution["executionArn"]
    print(f"Execution ARN:     {execution_arn}")

    print("\n[2/4] Monitoring State Machine Execution...")
    status = "RUNNING"
    for _ in range(40):
        desc = sfn_client.describe_execution(executionArn=execution_arn)
        status = desc["status"]
        if status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
            break
        time.sleep(1)

    print(f"Execution finished with status: {status}")

    # Print execution history events to observe task progression
    history = sfn_client.get_execution_history(executionArn=execution_arn, maxResults=50)
    print("\nState Machine Event Sequence:")
    for ev in history.get("events", []):
        ev_type = ev["type"]
        if "StateEntered" in ev_type:
            details = ev.get("stateEnteredEventDetails", {})
            print(f"  ▶ [ENTERED] {details.get('name')}")
        elif "StateExited" in ev_type:
            details = ev.get("stateExitedEventDetails", {})
            print(f"  ✔ [COMPLETED] {details.get('name')}")
        elif "ExecutionFailed" in ev_type:
            details = ev.get("executionFailedEventDetails", {})
            print(f"  ❌ [FAILED] {details.get('error')}: {details.get('cause')}")

    if status != "SUCCEEDED":
        sys.exit(1)

    print("\n[3/4] Step Function Execution Output:")
    output = json.loads(desc.get("output", "{}"))
    print(json.dumps(output, indent=2))

    print("\n[4/4] Verifying DynamoDB Job Run Record:")
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
    except Exception as e:
        print(f"DynamoDB check warning: {e}")

    # Verify S3 output
    try:
        processed_key = output.get("context", {}).get("processed_s3_key")
        if processed_key:
            s3_obj = s3_client.get_object(Bucket="etl-framework-processed-dev", Key=processed_key)
            content = json.loads(s3_obj["Body"].read().decode("utf-8"))
            print(f"\nVerified S3 processed output (s3://etl-framework-processed-dev/{processed_key}):")
            print(json.dumps(content, indent=2))
    except Exception as e:
        print(f"S3 check note: {e}")

if __name__ == "__main__":
    main()
