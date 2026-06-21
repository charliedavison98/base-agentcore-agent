#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

STAGE="production"
while [[ $# -gt 0 ]]; do
  case $1 in
    --stage) STAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "Building frontend (mode: $STAGE)..."
cd "$FRONTEND_DIR"
npm ci
npm run build -- --mode "$STAGE"
echo "Frontend build complete: $FRONTEND_DIR/dist"
