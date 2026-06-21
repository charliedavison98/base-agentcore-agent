#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Creates the GitHub Actions IAM role for CDK deployments via OIDC.
#
# The role has minimum permissions: it can only assume the four CDK bootstrap
# roles (deploy, file-publishing, image-publishing, lookup). All actual AWS
# resource permissions are handled by those bootstrap roles.
#
# Usage:
#   ./scripts/create-github-actions-role.sh --region eu-west-1
#
# The GitHub repo is auto-detected from git remote origin. Override with:
#   ./scripts/create-github-actions-role.sh --region eu-west-1 --repo your-org/your-repo
#
# Prerequisites:
#   - AWS CLI configured and authenticated (aws configure sso)
#   - CDK bootstrap already run in the target account/region
# ---------------------------------------------------------------------------

ROLE_NAME=""
REGION=""
GITHUB_REPO=""

usage() {
  echo "Usage: $0 --region <aws-region> [--repo <org/repo>] [--role-name <name>]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --repo)     GITHUB_REPO="$2"; shift 2 ;;
    --region)   REGION="$2";      shift 2 ;;
    --role-name) ROLE_NAME="$2";  shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$REGION" ]] && usage

# Auto-detect repo from git remote if not provided
if [[ -z "$GITHUB_REPO" ]]; then
  REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
  if [[ -z "$REMOTE_URL" ]]; then
    echo "Error: could not detect git remote. Pass --repo <org/repo> explicitly."
    exit 1
  fi
  # Handle both HTTPS (https://github.com/org/repo.git) and SSH (git@github.com:org/repo.git)
  GITHUB_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||' | sed 's|\.git$||')
fi

# Default role name derived from repo name if not overridden
if [[ -z "$ROLE_NAME" ]]; then
  REPO_NAME=$(echo "$GITHUB_REPO" | cut -d'/' -f2)
  ROLE_NAME="github-actions-${REPO_NAME}"
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
OIDC_PROVIDER="token.actions.githubusercontent.com"
OIDC_PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"

echo "Account:  ${ACCOUNT_ID}"
echo "Region:   ${REGION}"
echo "Repo:     ${GITHUB_REPO}"
echo "Role:     ${ROLE_NAME}"
echo ""

# ---------------------------------------------------------------------------
# 1. Create OIDC provider if it doesn't already exist
# ---------------------------------------------------------------------------
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "${OIDC_PROVIDER_ARN}" &>/dev/null; then
  echo "✓ OIDC provider already exists"
else
  echo "Creating OIDC provider..."
  aws iam create-open-id-connect-provider \
    --url "https://${OIDC_PROVIDER}" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"
  echo "✓ OIDC provider created"
fi

# ---------------------------------------------------------------------------
# 2. Trust policy — only tokens from this repo's main branch
# ---------------------------------------------------------------------------
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "${OIDC_PROVIDER}:sub": "repo:${GITHUB_REPO}:ref:refs/heads/main"
        }
      }
    }
  ]
}
EOF
)

# ---------------------------------------------------------------------------
# 3. Permission policy — assume CDK bootstrap roles only
# ---------------------------------------------------------------------------
PERMISSION_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": [
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-*-deploy-role-${ACCOUNT_ID}-${REGION}",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-*-file-publishing-role-${ACCOUNT_ID}-${REGION}",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-*-image-publishing-role-${ACCOUNT_ID}-${REGION}",
        "arn:aws:iam::${ACCOUNT_ID}:role/cdk-*-lookup-role-${ACCOUNT_ID}-${REGION}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "cloudformation:DescribeStacks",
      "Resource": "arn:aws:cloudformation:*:${ACCOUNT_ID}:stack/*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::*",
        "arn:aws:s3:::*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/*"
    }
  ]
}
EOF
)

# ---------------------------------------------------------------------------
# 4. Create or update the role
# ---------------------------------------------------------------------------
if aws iam get-role --role-name "${ROLE_NAME}" &>/dev/null; then
  echo "Role already exists — updating trust policy..."
  aws iam update-assume-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-document "${TRUST_POLICY}"
else
  echo "Creating role ${ROLE_NAME}..."
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "${TRUST_POLICY}" \
    --description "GitHub Actions CDK deployment role for ${GITHUB_REPO}"
fi

echo "Attaching permissions policy..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "CdkBootstrapRoleAccess" \
  --policy-document "${PERMISSION_POLICY}"

ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query Role.Arn --output text)

echo ""
echo "✓ Done. Add this to your GitHub repo secrets:"
echo ""
echo "  AWS_ROLE_ARN = ${ROLE_ARN}"
echo ""
echo "Make sure CDK bootstrap has been run in ${ACCOUNT_ID}/${REGION}:"
echo "  cd cdk && cdk bootstrap --context stage=prod"
