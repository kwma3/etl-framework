import json
import jobs  # Triggers auto-discovery of all jobs
from framework.registry import JobRegistry
from framework.dispatcher import TaskDispatcher

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Action: list all registered jobs
    if event.get("action") == "list_jobs":
        return {
            "statusCode": 200,
            "jobs": JobRegistry.list_jobs()
        }

    # Action: execute a specific task dispatched by Step Functions
    job_name = event.get("job_name")
    task_name = event.get("task_name")

    if not job_name or not task_name:
        raise ValueError("Payload must contain both 'job_name' and 'task_name'")

    return TaskDispatcher.dispatch(event)
