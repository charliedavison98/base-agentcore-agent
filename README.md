# AgentCore Chatbot Backend

A generic serverless AgentCore backend you can fork and build on. Provides a streaming chat API, Cognito auth, long-term memory, and Bedrock guardrails out of the box. Customise the prompt and tools in `agent/` to build your own agent.

**Stack:** AgentCore runtime (Docker) · API Gateway · Cognito · CDK (Python) · GitHub Actions (OIDC)

---

## One-time setup

### Prerequisites
- Python 3.11+, Node.js 22+, Docker Desktop
- AWS CLI configured (`aws configure sso`)

### AWS setup
1. **Enable Bedrock model access** for the model in `agent/agent.py` (Claude Sonnet 4) in your target region via the AWS console.

2. **Bootstrap CDK** (once per account/region):
```bash
cd cdk && cdk bootstrap --context stage=dev
```

### GitHub Actions (CI/CD)
The workflow at `.github/workflows/serverless-backend.yml` deploys on push to `main` using OIDC.

1. **Create the IAM role** using the provided script (minimum permissions — the role can only assume CDK bootstrap roles):
   ```bash
   ./scripts/create-github-actions-role.sh --region eu-west-1
   ```
   The repo is auto-detected from `git remote origin`. The role is named `github-actions-<repo-name>`. The script prints the ARN when done.
2. **Add secret** `AWS_ROLE_ARN` in your GitHub repo settings → Secrets.
3. **Set your region and stage** in the workflow:
```yaml
env:
  AWS_REGION: eu-west-1
  STAGE: prod
```

---

## Manual deployment

```bash
cd cdk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk deploy --context stage={stage}
```

Outputs: API Gateway URL, Cognito User Pool ID, Cognito Client ID.
