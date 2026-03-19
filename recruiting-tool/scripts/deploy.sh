#!/usr/bin/env bash
set -euo pipefail

# Deploy the recruiting tool to AWS
# Usage: ./scripts/deploy.sh [dev|staging|prod]

STAGE="${1:-prod}"
STACK_NAME="recruiting-tool"
[ "$STAGE" != "prod" ] && STACK_NAME="recruiting-tool-${STAGE}"

echo "==> Deploying recruiting-tool (stage: $STAGE, stack: $STACK_NAME)"

# Preflight checks
command -v sam >/dev/null 2>&1 || { echo "ERROR: AWS SAM CLI not installed. Run: brew install aws-sam-cli"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "ERROR: AWS CLI not installed."; exit 1; }

# Verify AWS credentials
aws sts get-caller-identity >/dev/null 2>&1 || { echo "ERROR: AWS credentials not configured. Run: aws configure"; exit 1; }
echo "  AWS account: $(aws sts get-caller-identity --query 'Account' --output text)"

# Run tests first
echo "==> Running tests..."
python -m pytest tests/ -v || { echo "ERROR: Tests failed. Fix before deploying."; exit 1; }

# Build
echo "==> Building..."
sam build

# Deploy
echo "==> Deploying..."
if [ "$STAGE" = "prod" ]; then
    sam deploy --parameter-overrides "Stage=$STAGE"
else
    sam deploy \
        --stack-name "$STACK_NAME" \
        --parameter-overrides "Stage=$STAGE" \
        --no-confirm-changeset
fi

# Show outputs
echo ""
echo "==> Stack outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Show API key
echo ""
echo "==> API Key:"
aws apigateway get-api-keys \
    --include-values \
    --query "items[?starts_with(name, \`$STACK_NAME\`)].{Name:name,Value:value}" \
    --output table

echo ""
echo "==> Done! Use the API key in the x-api-key header for all requests."
