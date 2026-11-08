import json
import os
import sys
import time
import uuid
import boto3
import pytest

# Add src to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from framework.registry import JobRegistry
import jobs  # Auto-discovers customer_orders & user_activity

ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.environ.get("AWS_REGION", "us-east-1")

@pytest.fixture(scope="session")
def aws_clients():
    return {
        "sfn": boto3.client("stepfunctions", endpoint_url=ENDPOINT_URL, region_name=REGION, aws_access_key_id="test", aws_secret_access_key="test"),
        "s3": boto3.client("s3", endpoint_url=ENDPOINT_URL, region_name=REGION, aws_access_key_id="test", aws_secret_access_key="test"),
        "dynamodb": boto3.client("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION, aws_access_key_id="test", aws_secret_access_key="test")
    }

@pytest.fixture(scope="session")
def state_machine_arn(aws_clients):
    sfn = aws_clients["sfn"]
    sms = sfn.list_state_machines().get("stateMachines", [])
    etl_sm = next((sm for sm in sms if "etl-framework-pipeline" in sm["name"]), None)
    assert etl_sm is not None, "Step Functions state machine 'etl-framework-pipeline' not found in LocalStack"
    return etl_sm["stateMachineArn"]

def test_job_registry_discovery():
    """Verify that both sample jobs are discovered in the registry."""
    job_names = [j["name"] for j in JobRegistry.list_jobs()]
    assert "customer_orders" in job_names
    assert "user_activity" in job_names

def test_customer_orders_execution(aws_clients, state_machine_arn):
    """Test full Step Functions pipeline execution for customer_orders."""
    sfn = aws_clients["sfn"]
    s3 = aws_clients["s3"]
    dynamodb = aws_clients["dynamodb"]

    job_id = f"test-ord-{uuid.uuid4().hex[:6]}"
    payload = {
        "job_name": "customer_orders",
        "job_id": job_id,
        "parameters": {},
        "context": {}
    }

    # 1. Start execution
    res = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=f"customer_orders-{job_id}",
        input=json.dumps(payload)
    )
    execution_arn = res["executionArn"]

    # 2. Wait for completion
    for _ in range(30):
        desc = sfn.describe_execution(executionArn=execution_arn)
        if desc["status"] != "RUNNING":
            break
        time.sleep(1)

    assert desc["status"] == "SUCCEEDED"

    # 3. Check S3 processed output
    processed_key = f"processed/{job_id}/clean_orders.json"
    obj = s3.get_object(Bucket="etl-framework-processed-dev", Key=processed_key)
    data = json.loads(obj["Body"].read().decode("utf-8"))
    assert data["job_id"] == job_id
    assert data["valid_count"] == 3
    assert data["rejected_count"] == 1
    assert data["orders"][0]["amount"] > 0

    # 4. Check DynamoDB tracking record
    ddb = dynamodb.query(
        TableName="etl-framework-metadata-dev",
        KeyConditionExpression="job_id = :jid",
        ExpressionAttributeValues={":jid": {"S": job_id}}
    )
    items = ddb.get("Items", [])
    assert len(items) == 1
    assert items[0]["status"]["S"] == "COMPLETED"
    assert items[0]["current_task"]["S"] == "load"

def test_user_activity_execution(aws_clients, state_machine_arn):
    """Test full Step Functions pipeline execution for user_activity."""
    sfn = aws_clients["sfn"]
    s3 = aws_clients["s3"]
    dynamodb = aws_clients["dynamodb"]

    job_id = f"test-usr-{uuid.uuid4().hex[:6]}"
    payload = {
        "job_name": "user_activity",
        "job_id": job_id,
        "parameters": {},
        "context": {}
    }

    # 1. Start execution
    res = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=f"user_activity-{job_id}",
        input=json.dumps(payload)
    )
    execution_arn = res["executionArn"]

    # 2. Wait for completion
    for _ in range(30):
        desc = sfn.describe_execution(executionArn=execution_arn)
        if desc["status"] != "RUNNING":
            break
        time.sleep(1)

    assert desc["status"] == "SUCCEEDED"

    # 3. Check S3 processed output for masked IPs
    processed_key = f"processed/{job_id}/clean_activity.json"
    obj = s3.get_object(Bucket="etl-framework-processed-dev", Key=processed_key)
    data = json.loads(obj["Body"].read().decode("utf-8"))
    assert data["job_id"] == job_id
    assert data["total_events"] == 4
    assert data["events"][0]["masked_ip"].endswith(".xxx")

    # 4. Check DynamoDB tracking record
    ddb = dynamodb.query(
        TableName="etl-framework-metadata-dev",
        KeyConditionExpression="job_id = :jid",
        ExpressionAttributeValues={":jid": {"S": job_id}}
    )
    items = ddb.get("Items", [])
    assert len(items) == 1
    assert items[0]["status"]["S"] == "COMPLETED"
    assert items[0]["current_task"]["S"] == "load"
