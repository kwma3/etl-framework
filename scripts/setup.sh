#!/usr/bin/env bash
set -euo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== 1. Starting LocalStack with Docker Compose ==="
cd "${ROOT_DIR}"
docker compose up -d

echo "=== 2. Waiting for LocalStack to be healthy ==="
MAX_RETRIES=30
RETRY_COUNT=0

until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"\|"s3": "running"' || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  echo "Waiting for LocalStack services to be ready... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
  sleep 2
  RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "Error: LocalStack failed to become ready in time."
  exit 1
fi
echo "LocalStack is running and healthy!"

echo "=== 3. Initializing and Applying Terraform ==="
cd "${ROOT_DIR}/terraform"

terraform init
terraform apply -auto-approve

echo ""
echo "=== Setup Complete! ==="
echo "You can now run ./scripts/trigger_etl.sh to test the pipeline."
