# Serverless ETL Framework (LocalStack + Terraform)

A modular, serverless ETL framework designed for local development and testing on [LocalStack](https://localstack.cloud/), provisioned declaratively with [Terraform](https://www.terraform.io/) and orchestrated using AWS services.

> For detailed design specifications, task abstractions, and concurrency scaling models, see the [Architecture & Design Guide](docs/architecture_design.md).

## Architecture Overview

```
                      +-------------------+
                      |    EventBridge    |
                      |  (Event Trigger)  |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |   Step Functions  |
                      |  (State Machine)  |
                      +----+----+----+----+
                           |    |    |
        +------------------+    |    +------------------+
        |                       |                       |
        v (task=extract)        v (task=transform)      v (task=load)
  +-----------------------------------------------------------+
  |              Unified Task Dispatcher Lambda               |
  |         (Framework Registry + Python ETL Jobs)            |
  +-----------------------------+-----------------------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
| S3 Raw Bucket |       | S3 Processed  |       | DynamoDB Table|
| (JSON Landing)|       | (Cleaned Data)|       | (Run Tracking)|
+---------------+       +---------------+       +---------------+
```

### Components

1. **AWS Step Functions**: Coordinates execution across tasks visually with native **1-Click Redrive** in the AWS / LocalStack web console:
   - **ExtractTask**: Ingests raw data and writes to the Raw S3 bucket.
   - **TransformTask**: Cleanses, filters, validates schemas, and writes to Processed S3 bucket.
   - **LoadTask**: Computes summaries, updates DynamoDB to `COMPLETED`, and finalizes the job.
2. **Unified Task Dispatcher Lambda**: Single Lambda function housing the job catalog (`JobRegistry`) and executing the specific task requested by Step Functions.
3. **EventBridge**: Ingests trigger events (`etl.trigger` / `StartETLJob`) and launches Step Functions workflows.
4. **Amazon S3**:
   - `etl-framework-raw-dev`: Landing bucket for raw input datasets.
   - `etl-framework-processed-dev`: Destination bucket for cleaned, transformed data.
5. **Amazon DynamoDB**:
   - `etl-framework-metadata-dev`: Partition key `job_id`, sort key `timestamp` tracking job progress, record counts, and errors.
6. **LocalStack**: Local emulation container for all above AWS services on `localhost:4566`.

---

## Directory Structure

```
etl_framework/
├── docker-compose.yml       # LocalStack container configuration
├── Makefile                 # Developer lifecycle commands (up, deploy, test-etl, list-jobs)
├── README.md                # Documentation and architectural guide
├── requirements.txt         # boto3 & testing dependencies
├── docs/
│   └── architecture_design.md # Full design specifications & ASL reference
├── scripts/
│   ├── setup.sh             # Starts LocalStack and provisions Terraform
│   ├── trigger_pipeline.py  # Step Functions execution & validation runner
│   ├── query_dynamodb.py    # Formatted terminal viewer for DynamoDB records
│   └── cleanup.sh           # Destroys Terraform state and stops LocalStack
├── src/
│   ├── framework/           # Core framework (base, context, registry, dispatcher)
│   ├── jobs/                # Registered Python ETL jobs (customer_orders, etc.)
│   └── lambda_dispatcher.py # Unified Lambda entrypoint
└── terraform/               # Declarative IaC
    ├── asl/
    │   └── etl_pipeline.asl.json # Amazon States Language pipeline definition
    ├── provider.tf
    ├── variables.tf
    ├── s3.tf
    ├── dynamodb.tf
    ├── iam.tf
    ├── lambdas.tf           # Packages unified dispatcher Lambda
    ├── step_functions.tf    # Loads ASL definition via templatefile
    ├── eventbridge.tf
    └── outputs.tf
```
    ├── provider.tf
    ├── variables.tf
    ├── s3.tf
    ├── dynamodb.tf
    ├── iam.tf
    ├── lambdas.tf
    ├── step_functions.tf
    ├── eventbridge.tf
    └── outputs.tf
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.0)
- Python 3.9+ with `boto3` (`pip install -r requirements.txt`)

### 1. Automated Setup

Run the setup script to start LocalStack and deploy the Terraform stack:

```bash
./scripts/setup.sh
```

Or using `make`:

```bash
make up
make deploy
```

### 2. Run and Verify an End-to-End ETL Job

Trigger a Step Functions execution and follow its status:

```bash
make run-job JOB=customer_orders
```

Inspect the DynamoDB execution metadata:

```bash
make query-ddb
```

Inspect the CloudWatch Monitoring Dashboard:

```bash
make view-dashboard
```

Launch the real-time visual web dashboard in your browser:

```bash
make dashboard
```
> Opens [http://localhost:8080](http://localhost:8080) with live auto-refresh, Step Functions execution feed, and 1-click job runners.

### 3. Cleanup

To tear down all provisioned resources and stop LocalStack:

```bash
./scripts/cleanup.sh
```

Or:

```bash
make down
```
