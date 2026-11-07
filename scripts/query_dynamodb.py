#!/usr/bin/env python3
import json
import os
import boto3

ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = "etl-framework-metadata-dev"

def main():
    dynamodb = boto3.client(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

    print(f"\nScanning DynamoDB table: {TABLE_NAME} (at {ENDPOINT_URL})\n")
    try:
        response = dynamodb.scan(TableName=TABLE_NAME)
        items = response.get("Items", [])
        if not items:
            print("No records found in table.")
            return

        print(f"{'Job ID':<18} | {'Status':<12} | {'Valid':<6} | {'Filtered':<8} | {'Raw S3 Key':<35} | {'Completed At'}")
        print("-" * 115)
        for item in sorted(items, key=lambda x: x.get("timestamp", {}).get("S", ""), reverse=True):
            jid = item.get("job_id", {}).get("S", "N/A")
            status = item.get("status", {}).get("S", "N/A")
            valid = item.get("valid_count", {}).get("N", "-")
            filtered = item.get("filtered_count", {}).get("N", "-")
            raw_key = item.get("raw_s3_key", {}).get("S", "N/A")
            completed = item.get("completed_at", {}).get("S", "N/A")
            print(f"{jid:<18} | {status:<12} | {valid:<6} | {filtered:<8} | {raw_key:<35} | {completed}")
        print("\n")
    except Exception as e:
        print(f"Error querying DynamoDB: {e}")

if __name__ == "__main__":
    main()
