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

echo "=== Step 1/3: Generating .env.${STAGE} from stack outputs ==="
"$SCRIPT_DIR/generate_env.sh" --stage "$STAGE"

echo "=== Step 2/3: Building frontend ==="
"$SCRIPT_DIR/build-frontend.sh" --stage "$STAGE"

echo "=== Step 3/3: Deploying to S3 + CloudFront ==="
"$SCRIPT_DIR/sync_frontend.sh" --stage "$STAGE"

echo "=== Done ==="
