# Project Overview: Extensible Serverless Python ETL Framework

This repository implements an extensible, serverless Python ETL (Extract, Transform, Load) framework designed for local development and testing via LocalStack (AWS Step Functions, Lambda, S3, DynamoDB, EventBridge), provisioned declaratively with Terraform.

---

## 1. Core Architecture & Philosophy

- **Unified Dispatcher (No Micro-Lambda Sprawl)**:
  All job execution routes through a single Lambda function (`etl-framework-dispatcher-dev`). The dispatcher dynamically loads and runs tasks for any registered job.
- **Single Shared State Machine**:
  A single generic Step Functions pipeline (`etl-framework-pipeline-dev`) orchestrates standard 3-stage workflows (`ExtractTask` ➔ `TransformTask` ➔ `LoadTask`). Adding a new Python ETL job does **not** require any Terraform changes or new ASL definitions.
- **S3 Data Pointer Pattern (256 KB Limit Protection)**:
  AWS Step Functions enforces a strict 256 KB execution payload limit. Heavy data payloads are saved directly to S3 (`etl-framework-raw-dev` and `etl-framework-processed-dev`). Step Functions state passes only lightweight metadata references (`job_id`, `s3_key`, status).
- **Execution Naming Convention**:
  Executions are prefixed as `{job_name}-{job_id}` (e.g., `customer_orders-job-c4a1792e-3331...`), allowing easy identification and filtering in the LocalStack Web Management Console (`app.localstack.cloud`).
- **State Tracking & Console Redrive**:
  Execution status and metrics are persisted in DynamoDB (`etl-framework-metadata-dev`, PK: `job_id`, SK: `timestamp`). Step Functions native 1-click **"Redrive Execution"** is supported for resuming failed executions.

---

## 2. Repository Layout

```text
etl_framework/
├── .env                       # LocalStack auth token (LOCALSTACK_AUTH_TOKEN)
├── Makefile                   # Unified workflow commands (up, deploy, test, run, query)
├── docker-compose.yml         # LocalStack container configuration (latest image)
├── requirements.txt           # Python dependencies (boto3, pytest)
├── docs/
│   └── architecture_design.md # Detailed architecture, ASL spec, scaling analysis
├── scripts/
│   ├── setup.sh               # LocalStack initialization & readiness check
│   ├── trigger_pipeline.py    # CLI tool to trigger Step Functions runs with job prefix
│   ├── query_dynamodb.py      # Formatted CLI viewer for execution logs
│   ├── view_dashboard.py      # Formatted CLI viewer for CloudWatch Dashboard
│   ├── serve_dashboard.py     # Local interactive web monitor server (port 8080)
│   └── cleanup.sh             # Teardown script
├── src/
│   ├── lambda_dispatcher.py   # Lambda entrypoint (routes list_jobs & task execution)
│   ├── framework/
│   │   ├── base.py            # Abstract ETLTask & ETLJob definitions
│   │   ├── context.py         # ETLContext (S3 helpers, metadata, DynamoDB tracking)
│   │   ├── dispatcher.py      # TaskDispatcher (retries, execution, status transitions)
│   │   └── registry.py        # JobRegistry & @register_job decorator
│   └── jobs/
│       ├── __init__.py        # Auto-discovers all Python modules in src/jobs/
│       ├── customer_orders.py # Sample Job 1 (e-commerce orders ETL)
│       └── user_activity.py   # Sample Job 2 (web analytics ETL with IP masking)
├── terraform/
│   ├── provider.tf            # AWS provider (pinned to 5.66.0, points to localhost:4566)
│   ├── variables.tf           # Environment, project name, region config
│   ├── step_functions.tf      # Step Functions state machine definition
│   ├── lambdas.tf             # Lambda packaging (src/ -> zip) and deployment
│   ├── monitoring.tf          # CloudWatch Dashboard for pipeline and task metrics
│   ├── s3.tf                  # Raw and Processed S3 buckets
│   ├── dynamodb.tf            # Metadata and audit DynamoDB table
│   ├── eventbridge.tf         # EventBridge event bus and trigger rule
│   ├── iam.tf                 # IAM roles and execution policies
│   └── asl/
│       └── etl_pipeline.asl.json # Generic 3-step state machine ASL
└── tests/
    └── test_poc_pipeline.py   # Pytest suite verifying job discovery and execution
```

---

## 3. How to Add a New ETL Job

To introduce a new ETL pipeline without touching Terraform:
1. Create a new file in `src/jobs/<job_name>.py`.
2. Define tasks extending `ETLTask` (`extract`, `transform`, `load`).
3. Instantiate and register the job using `@register_job("<job_name>")`:

```python
from framework.base import ETLJob, ETLTask
from framework.context import ETLContext
from framework.registry import register_job

class Extract(ETLTask):
    def execute(self, context: ETLContext) -> dict:
        # Fetch data, write raw data to context.write_s3_data(..., "raw/...")
        return {"status": "SUCCESS", "records_extracted": 100}

class Transform(ETLTask):
    def execute(self, context: ETLContext) -> dict:
        # Read raw data, transform, write to context.write_s3_data(..., "processed/...")
        return {"status": "SUCCESS", "records_transformed": 100}

class Load(ETLTask):
    def execute(self, context: ETLContext) -> dict:
        # Read processed data, commit / load
        return {"status": "SUCCESS", "records_loaded": 100}

@register_job("my_new_job")
def create_job() -> ETLJob:
    return ETLJob(
        name="my_new_job",
        description="Description of new job",
        tasks=[Extract("extract"), Transform("transform"), Load("load")]
    )
```

4. Deploy the updated code:
   ```bash
   make deploy
   ```
5. Run the job:
   ```bash
   make run-job JOB=my_new_job
   ```

---

## 4. Common CLI Runbook

Always activate `.venv` or run through `make` (which uses `.venv/bin/python3`):

| Action | Command | Notes |
| :--- | :--- | :--- |
| **Start LocalStack** | `make up` | Starts `etl_localstack` container on port 4566 |
| **Deploy Stack** | `make deploy` | Packages Lambda and applies Terraform |
| **Run Tests** | `make test` | Runs pytest suite against LocalStack |
| **List Registered Jobs**| `make list-jobs` | Queries Lambda dispatcher for registered jobs |
| **Execute Job** | `make run-job JOB=customer_orders` | Triggers Step Functions execution |
| **Inspect DynamoDB Logs**| `make query-ddb` | Displays formatted execution history |
| **View CloudWatch Dashboard**| `make view-dashboard` | Inspects metrics dashboard layout & config |
| **Launch Live Web Dashboard**| `make dashboard` | Starts local browser monitor on port 8080 |
| **Stop Infrastructure** | `make down` | Stops and removes LocalStack container |

---

## 5. Critical Technical Constraints & Gotchas

1. **Terraform AWS Provider Version**:
   - Pinned strictly to `5.66.0` in `terraform/provider.tf`.
   - *Reason*: AWS provider versions `>= 5.67.0` perform plan-time ASL validation that fails against LocalStack with `ValidateStateMachineDefinition: 501 Not Implemented`. Do not upgrade without testing.
2. **LocalStack Licensing**:
   - Requires `LOCALSTACK_AUTH_TOKEN` in `.env` or system environment for Step Functions & pro feature emulation.
3. **DynamoDB Timestamp Consistency**:
   - The table uses composite primary key `(job_id [HASH], timestamp [RANGE])`.
   - When a job transitions through tasks (`extract` ➔ `transform` ➔ `load`), `dispatcher.py` retains `start_timestamp` in `context.state` so that `update_item` correctly modifies the initial execution record rather than creating orphan records.
4. **Environment PATH on macOS**:
   - Docker CLI (`/Applications/Docker.app/Contents/Resources/bin`) and Terraform (`/opt/homebrew/bin`) must be in `$PATH`.
