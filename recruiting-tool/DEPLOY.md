# Deployment Runbook

Step-by-step guide for deploying the recruiting tool to AWS.

## Prerequisites

1. **AWS CLI** (v2+)
   ```bash
   brew install awscli
   aws --version
   ```

2. **AWS SAM CLI**
   ```bash
   brew install aws-sam-cli
   sam --version
   ```

3. **Python 3.12** (for local builds and tests)
   ```bash
   python3 --version
   ```

4. **AWS credentials configured** with permissions for CloudFormation, Lambda, API Gateway, DynamoDB, S3, and IAM
   ```bash
   aws configure
   # Verify:
   aws sts get-caller-identity
   ```

5. **Environment variables** — copy `.env.example` to `.env` and fill in Slack tokens, Indeed API keys, etc. These are passed as SAM parameter overrides in `samconfig.toml`.

## Deploy to Dev

```bash
# Build + deploy (no changeset confirmation)
sam build && sam deploy --config-env dev
```

Or use the Makefile:
```bash
make deploy-dev
```

Or use the deploy script:
```bash
./scripts/deploy.sh dev
```

**Dev stack name**: `recruiting-tool-dev`

## Deploy to Prod

```bash
# Build + deploy (will prompt to confirm changeset)
sam build && sam deploy
```

Or use the Makefile:
```bash
make deploy
```

Or use the deploy script:
```bash
./scripts/deploy.sh prod
```

**Prod stack name**: `recruiting-tool`

## Verify Deployment

### 1. Check CloudFormation stack status

```bash
# Prod
aws cloudformation describe-stacks \
  --stack-name recruiting-tool \
  --query 'Stacks[0].StackStatus' \
  --output text
# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# Dev
aws cloudformation describe-stacks \
  --stack-name recruiting-tool-dev \
  --query 'Stacks[0].StackStatus' \
  --output text
```

### 2. Get stack outputs (API URL, table name)

```bash
make outputs
# Or:
aws cloudformation describe-stacks \
  --stack-name recruiting-tool \
  --query 'Stacks[0].Outputs' \
  --output table
```

### 3. Get API key

```bash
make api-key
# Or:
aws apigateway get-api-keys \
  --include-values \
  --query 'items[?starts_with(name, `recruiting-tool`)].value' \
  --output text
```

### 4. Test health endpoint

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name recruiting-tool \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

curl -s "$API_URL/health" | python3 -m json.tool
```

### 5. Test authenticated endpoint

```bash
API_KEY=$(make api-key 2>/dev/null)
curl -s -H "x-api-key: $API_KEY" "$API_URL/jobs" | python3 -m json.tool
```

### 6. Check Lambda in AWS Console

- Open [Lambda Console](https://console.aws.amazon.com/lambda)
- Filter by `recruiting-tool` — all functions should show "Last modified" matching deploy time
- Click any function > Monitor > View CloudWatch Logs to verify no startup errors

## Update After Changes

Re-run the same deploy command. SAM handles incremental updates:

```bash
sam build && sam deploy            # prod
sam build && sam deploy --config-env dev  # dev
```

CloudFormation creates a changeset showing exactly what will change before applying.

## Rollback

### Automatic rollback

CloudFormation automatically rolls back if a deploy fails mid-way. No action needed.

### Manual rollback to previous version

```bash
# List recent CloudFormation events to find the last good state
aws cloudformation describe-stack-events \
  --stack-name recruiting-tool \
  --query 'StackEvents[?ResourceStatus==`UPDATE_COMPLETE`].[Timestamp,LogicalResourceId]' \
  --output table \
  --max-items 20

# Roll back to previous deployment
aws cloudformation rollback-stack --stack-name recruiting-tool

# Or redeploy a known-good commit
git checkout <good-commit-hash>
sam build && sam deploy
```

### Rollback a single Lambda (fast)

```bash
# List versions
aws lambda list-versions-by-function --function-name recruiting-tool-HealthFunction

# Point alias to previous version
aws lambda update-alias \
  --function-name recruiting-tool-HealthFunction \
  --name live \
  --function-version <previous-version>
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `CREATE_FAILED: recruiting-tool already exists` | Stack name collision | Use a different stack name or delete the old stack first |
| `Error: No such option: --guided` | Old SAM CLI version | `brew upgrade aws-sam-cli` |
| `Unable to locate credentials` | AWS creds not set | `aws configure` or export `AWS_PROFILE` |
| `ROLLBACK_COMPLETE` state | Previous deploy failed | Delete stack: `sam delete --stack-name recruiting-tool` then redeploy |
| `Template format error` | Invalid template.yaml | Run `sam validate` to check syntax |
| `Resource limit exceeded` | Too many Lambda functions | Check service quotas in AWS Console |
| `Build failed: requirements.txt` | Missing Python deps | `pip install -r requirements.txt` locally to verify |
| `CAPABILITY_IAM required` | Missing capability flag | Already set in `samconfig.toml` — don't override manually |

## Post-Deploy Checklist

- [ ] Stack status is `UPDATE_COMPLETE` or `CREATE_COMPLETE`
- [ ] Health endpoint returns 200: `curl $API_URL/health`
- [ ] API key auth works: `curl -H "x-api-key: $KEY" $API_URL/jobs`
- [ ] Slack notification test: create a test candidate and verify notification in `#recruiting`
- [ ] Indeed webhook endpoint is reachable: `POST $API_URL/indeed/apply`
- [ ] DynamoDB table exists and is accessible: `aws dynamodb describe-table --table-name recruiting-candidates`
- [ ] S3 assets bucket exists: `aws s3 ls | grep recruiting`
- [ ] CloudWatch logs are flowing (invoke any endpoint, check logs)
- [ ] No error alarms firing in CloudWatch

## Monitoring

```bash
# Tail logs for a specific function
make logs-Health
make logs-CreateJob
# Pattern: make logs-<FunctionLogicalId without "Function" suffix>

# Or directly:
sam logs -n HealthFunction --stack-name recruiting-tool --tail
```
