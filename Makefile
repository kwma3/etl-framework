export PATH := /Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin:/usr/local/bin:$(HOME)/.local/bin:$(PATH)

ENV_FLAG := $(shell [ -f $(HOME)/.env ] && echo "--env-file $(HOME)/.env")

.PHONY: help up down deploy destroy test test-etl list-jobs run-job query-ddb logs status

help:
	@echo "Available commands:"
	@echo "  make up         - Start LocalStack via Docker Compose"
	@echo "  make deploy     - Initialize and apply Terraform resources"
	@echo "  make test       - Run full pytest integration test suite"
	@echo "  make test-etl   - Trigger Step Functions ETL run (customer_orders)"
	@echo "  make list-jobs  - List all registered jobs in Lambda catalog"
	@echo "  make run-job    - Run specific job (e.g. make run-job JOB=customer_orders)"
	@echo "  make query-ddb  - View all job run records in DynamoDB"
	@echo "  make logs       - Follow LocalStack logs"
	@echo "  make status     - Check LocalStack health"
	@echo "  make destroy    - Tear down Terraform resources"
	@echo "  make down       - Stop LocalStack and clean up containers"

test:
	.venv/bin/pytest -v tests/

up:
	docker compose $(ENV_FLAG) up -d
	@echo "Waiting for LocalStack to become healthy..."
	@until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"\|"s3": "running"'; do sleep 1; done
	@echo "LocalStack is up and running."

deploy:
	cd terraform && terraform init && terraform apply -auto-approve

test-etl:
	.venv/bin/python3 scripts/trigger_pipeline.py

list-jobs:
	.venv/bin/python3 scripts/trigger_pipeline.py --list

run-job:
	.venv/bin/python3 scripts/trigger_pipeline.py --job $(or $(JOB),customer_orders) --params '$(or $(PARAMS),{})'

query-ddb:
	.venv/bin/python3 scripts/query_dynamodb.py

view-dashboard:
	.venv/bin/python3 scripts/view_dashboard.py

dashboard:
	.venv/bin/python3 scripts/serve_dashboard.py

logs:
	docker compose logs -f localstack

status:
	curl -s http://localhost:4566/_localstack/health | python3 -m json.tool

destroy:
	cd terraform && terraform destroy -auto-approve

down:
	./scripts/cleanup.sh
