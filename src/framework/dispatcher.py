import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict
from .registry import JobRegistry
from .context import ETLContext

class TaskDispatcher:
    """Executes a single task within a registered ETL job and updates DynamoDB tracking."""

    @staticmethod
    def dispatch(payload: Dict[str, Any]) -> Dict[str, Any]:
        job_name = payload["job_name"]
        task_name = payload["task_name"]
        job_id = payload.get("job_id", f"job-{int(time.time())}")
        parameters = payload.get("parameters", {})
        incoming_state = payload.get("context", {})

        context = ETLContext(
            job_id=job_id,
            job_name=job_name,
            task_name=task_name,
            parameters=parameters,
            state=incoming_state
        )

        job = JobRegistry.get(job_name)
        task = job.get_task(task_name)

        start_time = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        start_timestamp = incoming_state.get("start_timestamp")
        if not start_timestamp:
            start_timestamp = now_iso
            context.state["start_timestamp"] = start_timestamp

        # Update initial DynamoDB status for the task
        try:
            context.dynamodb_client.update_item(
                TableName=context.metadata_table,
                Key={
                    "job_id": {"S": job_id},
                    "timestamp": {"S": start_timestamp}
                },
                UpdateExpression="SET job_name = :jname, current_task = :tname, updated_at = :now, #s = :status",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":jname": {"S": job_name},
                    ":tname": {"S": task_name},
                    ":now": {"S": now_iso},
                    ":status": {"S": "IN_PROGRESS"}
                }
            )
        except Exception:
            context.dynamodb_client.put_item(
                TableName=context.metadata_table,
                Item={
                    "job_id": {"S": job_id},
                    "timestamp": {"S": start_timestamp},
                    "job_name": {"S": job_name},
                    "current_task": {"S": task_name},
                    "status": {"S": "IN_PROGRESS"},
                    "updated_at": {"S": now_iso}
                }
            )

        # Execute task with retries
        last_error = None
        for attempt in range(task.max_retries + 1):
            try:
                task_output = task.execute(context)
                if isinstance(task_output, dict):
                    context.state.update(task_output)
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt < task.max_retries:
                    time.sleep(task.backoff_seconds * (2 ** attempt))

        duration_ms = int((time.time() - start_time) * 1000)
        end_iso = datetime.now(timezone.utc).isoformat()

        if last_error:
            # Record failure in DynamoDB
            err_msg = str(last_error)
            stack = traceback.format_exc()
            context.dynamodb_client.update_item(
                TableName=context.metadata_table,
                Key={
                    "job_id": {"S": job_id},
                    "timestamp": {"S": context.state.get("start_timestamp", now_iso)}
                },
                UpdateExpression="SET #s = :status, failed_task = :tname, error_message = :err, updated_at = :now",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":status": {"S": "FAILED"},
                    ":tname": {"S": task_name},
                    ":err": {"S": f"{err_msg}\n{stack}"},
                    ":now": {"S": end_iso}
                }
            )
            raise RuntimeError(f"Task '{task_name}' in job '{job_name}' failed: {err_msg}") from last_error

        # If this is the final/terminal task, mark COMPLETED
        is_final = payload.get("is_final", False)
        if is_final:
            context.dynamodb_client.update_item(
                TableName=context.metadata_table,
                Key={
                    "job_id": {"S": job_id},
                    "timestamp": {"S": start_timestamp}
                },
                UpdateExpression="SET #s = :status, current_task = :tname, completed_at = :completed, updated_at = :now",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":status": {"S": "COMPLETED"},
                    ":tname": {"S": task_name},
                    ":completed": {"S": end_iso},
                    ":now": {"S": end_iso}
                }
            )

        return {
            "statusCode": 200,
            "job_id": job_id,
            "job_name": job_name,
            "task_name": task_name,
            "duration_ms": duration_ms,
            "parameters": parameters,
            "context": context.state,
            "metrics": context.metrics
        }
