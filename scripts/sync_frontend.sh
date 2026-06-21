#!/bin/bash
set -e

STAGE="dev"
while [[ $# -gt 0 ]]; do
  case $1 in
    --stage) STAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

STACK_NAME="SimpleChatbot-${STAGE}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/../frontend/dist"

if [[ ! -d "$DIST_DIR" ]]; then
  echo "Error: $DIST_DIR not found. Run ./scripts/build-frontend.sh --stage $STAGE first." >&2
  exit 1
fi

echo "Reading outputs from ${STACK_NAME}..."

get_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

BUCKET=$(get_output "FrontendBucketName")
DIST_ID=$(get_output "CloudFrontDistributionId")
WEBSITE_URL=$(get_output "WebsiteUrl")

if [[ -z "$BUCKET" || -z "$DIST_ID" ]]; then
  echo "Error: FrontendBucketName or CloudFrontDistributionId missing from stack outputs." >&2
  exit 1
fi

echo "Syncing $DIST_DIR → s3://${BUCKET}/"
aws s3 sync "$DIST_DIR" "s3://${BUCKET}/" --delete

echo "Invalidating CloudFront distribution ${DIST_ID}..."
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" --output text

echo "Done. Website: ${WEBSITE_URL}"
