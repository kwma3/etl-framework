#!/usr/bin/env bash
set -euo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== 1. Destroying Terraform Managed Resources ==="
cd "${ROOT_DIR}/terraform"
if [ -f "terraform.tfstate" ]; then
  terraform destroy -auto-approve || true
fi

echo "=== 2. Tearing Down LocalStack Container ==="
cd "${ROOT_DIR}"
docker compose down -v

echo "=== Cleaned up successfully ==="
