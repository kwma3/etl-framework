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
                      +----+---------+----+
                           |         |
         +-----------------+         +-----------------+
         |                           |                 |
         v                           v                 v
+-----------------+         +-----------------+  +---------------+
| Extract Lambda  |         |Transform Lambda |  |  Load Lambda  |
+--------+--------+         +--------+--------+  +-------+-------+
         |                           |                   |
         v                           v                   v
+-----------------+         +-----------------+  +---------------+
|  S3 Raw Bucket  |         |  S3 Processed   |  | EventBridge / |
| (JSON Landing)  |         | (Cleaned Data)  |  | DynamoDB Log  |
+-----------------+         +-----------------+  +---------------+
         \                           /                   /
          \                         /                   /
           +-----------------------+-------------------+
                                   |
                                   v
                         +-------------------+
                         | DynamoDB Metadata |
                         | (Job Runs Table)  |
                         +-------------------+
```

### Components

1. **EventBridge**: Ingests pipeline trigger events (`etl.trigger` / `StartETLJob`) and invokes the Step Functions workflow.
2. **AWS Step Functions**: Coordinates execution across tasks:
   - **Extract**: Fetches raw data batches and saves them to the Raw S3 bucket.
   - **Transform**: Reads raw data, validates email format and transaction amounts, cleans schemas, and writes to Processed S3 bucket.
   - **Load / Finalize**: Emits completion events and writes final execution status to DynamoDB.
3. **AWS Lambda (Python 3.11)**: Lightweight, modular task workers (`src/lambdas/`).
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
├── Makefile                 # Convenient developer lifecycle commands
├── README.md                # Documentation and architectural guide
├── requirements.txt         # Python dependencies for local scripts / testing
├── scripts/
│   ├── setup.sh             # Starts LocalStack and provisions Terraform
│   ├── trigger_etl.py       # End-to-end execution and validation runner
│   ├── trigger_etl.sh       # Shell wrapper for trigger_etl.py
│   └── cleanup.sh           # Destroys Terraform state and stops LocalStack
├── src/
│   └── lambdas/             # Python Lambda handlers
│       ├── common/          # Shared LocalStack client utilities
│       ├── extract/         # Raw data ingestion handler
│       ├── transform/       # Cleaning, validation, transformation handler
│       └── load/            # Final status update & notification handler
└── terraform/               # Declarative IaC (AWS Provider configured for LocalStack)
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

Execute the verification script to start a Step Functions execution, follow its status, and inspect DynamoDB and S3 outputs:

```bash
./scripts/trigger_etl.sh
```

Or:

```bash
make test-etl
```

### 3. Cleanup

To tear down all provisioned resources and stop LocalStack:

```bash
./scripts/cleanup.sh
```

Or:

```bash
make down
```
