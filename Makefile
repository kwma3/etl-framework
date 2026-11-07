export PATH := /Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin:/usr/local/bin:$(HOME)/.local/bin:$(PATH)

ENV_FLAG := $(shell [ -f $(HOME)/.env ] && echo "--env-file $(HOME)/.env")

.PHONY: help up down deploy destroy test-etl query-ddb logs status

help:
	@echo "Available commands:"
	@echo "  make up        - Start LocalStack via Docker Compose"
	@echo "  make deploy    - Initialize and apply Terraform resources"
	@echo "  make test-etl  - Trigger and verify an end-to-end ETL run"
	@echo "  make query-ddb - View all job run records in DynamoDB"
	@echo "  make logs      - Follow LocalStack logs"
	@echo "  make status    - Check LocalStack health"
	@echo "  make destroy   - Tear down Terraform resources"
	@echo "  make down      - Stop LocalStack and clean up containers"

up:
	docker compose $(ENV_FLAG) up -d
	@echo "Waiting for LocalStack to become healthy..."
	@until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"\|"s3": "running"'; do sleep 1; done
	@echo "LocalStack is up and running."

deploy:
	cd terraform && terraform init && terraform apply -auto-approve

test-etl:
	./scripts/trigger_etl.sh

query-ddb:
	.venv/bin/python3 scripts/query_dynamodb.py

logs:
	docker compose logs -f localstack

status:
	curl -s http://localhost:4566/_localstack/health | python3 -m json.tool

destroy:
	cd terraform && terraform destroy -auto-approve

down:
	./scripts/cleanup.sh
