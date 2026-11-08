#!/usr/bin/env python3
"""
CLI utility to inspect the CloudWatch Monitoring Dashboard in LocalStack.
"""
import json
import boto3

ENDPOINT_URL = "http://localhost:4566"
REGION = "us-east-1"
DASHBOARD_NAME = "etl-framework-monitoring-dev"

def view_dashboard():
    client = boto3.client(
        "cloudwatch",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    try:
        response = client.get_dashboard(DashboardName=DASHBOARD_NAME)
    except Exception as e:
        print(f"❌ Error fetching dashboard '{DASHBOARD_NAME}': {e}")
        return

    body = json.loads(response.get("DashboardBody", "{}"))
    widgets = body.get("widgets", [])

    print("\n" + "=" * 80)
    print(f"📊 CLOUDWATCH DASHBOARD: {response['DashboardName']}")
    print(f"ARN: {response.get('DashboardArn')}")
    print(f"Total Configured Widgets: {len(widgets)}")
    print("=" * 80)

    for idx, widget in enumerate(widgets, 1):
        w_type = widget.get("type", "unknown")
        props = widget.get("properties", {})
        title = props.get("title", "Header / Notes")
        w_width = widget.get("width", 0)
        w_height = widget.get("height", 0)

        print(f"\n[{idx}] {title} (Type: {w_type}, Size: {w_width}x{w_height})")

        if w_type == "text":
            print("    Markdown Content:")
            for line in props.get("markdown", "").strip().split("\n"):
                print(f"      {line}")
        elif w_type == "metric":
            print(f"    View: {props.get('view')}, Period: {props.get('period')}s, Stat: {props.get('stat', 'Custom')}")
            print("    Monitored Metrics:")
            for m in props.get("metrics", []):
                # Standard metric shape: [Namespace, MetricName, DimensionName, DimensionValue, ConfigDict?]
                namespace = m[0]
                metric_name = m[1]
                dim = f"{m[2]}={m[3].split('/')[-1] if '/' in m[3] else m[3]}" if len(m) > 3 else "None"
                label = ""
                if len(m) > 4 and isinstance(m[4], dict):
                    if "label" in m[4]:
                        label = f" (Label: {m[4]['label']})"
                    elif "color" in m[4]:
                        label = f" (Color: {m[4]['color']})"
                print(f"      • [{namespace}] {metric_name} [{dim}]{label}")

    print("\n" + "=" * 80)
    print("🌐 View in Web Console:")
    print("   Open https://app.localstack.cloud -> CloudWatch -> Dashboards")
    print(f"   Select: '{DASHBOARD_NAME}'")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    view_dashboard()
