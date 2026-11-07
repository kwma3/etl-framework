import os
import boto3

def get_endpoint_url():
    """Resolves the endpoint URL for LocalStack / AWS."""
    # Standard AWS SDK endpoint URL override
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    if endpoint:
        return endpoint
    
    # In LocalStack Lambda container, LOCALSTACK_HOSTNAME is usually set
    localstack_hostname = os.environ.get("LOCALSTACK_HOSTNAME")
    if localstack_hostname:
        edge_port = os.environ.get("EDGE_PORT", "4566")
        return f"http://{localstack_hostname}:{edge_port}"
        
    return None

def get_boto3_client(service_name: str):
    """Instantiates a boto3 client targeting LocalStack if configured."""
    endpoint_url = get_endpoint_url()
    region_name = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client(
        service_name,
        region_name=region_name,
        endpoint_url=endpoint_url
    )

def get_boto3_resource(service_name: str):
    """Instantiates a boto3 resource targeting LocalStack if configured."""
    endpoint_url = get_endpoint_url()
    region_name = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.resource(
        service_name,
        region_name=region_name,
        endpoint_url=endpoint_url
    )
