#!/bin/bash
set -e

STAGE="dev"
while [[ $# -gt 0 ]]; do
  case $1 in
    --stage) STAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDK_DIR="$SCRIPT_DIR/../cdk"

echo "=== Deploying backend (stage: $STAGE) ==="
cd "$CDK_DIR"
source .venv/bin/activate
cdk deploy --context stage="$STAGE" --require-approval never

echo "=== Deploying frontend (stage: $STAGE) ==="
"$SCRIPT_DIR/deploy_frontend.sh" --stage "$STAGE"

echo "=== All done ==="
