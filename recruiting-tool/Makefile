.PHONY: build deploy deploy-dev test test-cov local clean

# Build the SAM application
build:
	sam build

# Deploy to production (confirms changeset)
deploy: build
	sam deploy

# Deploy to dev (no changeset confirmation)
deploy-dev: build
	sam deploy --config-env dev

# Run tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Start local API for development
local: build
	sam local start-api --warm-containers EAGER

# Invoke a single function locally
invoke-%: build
	sam local invoke $*Function --event events/$*.json

# Show stack outputs (API URL, table name, etc.)
outputs:
	aws cloudformation describe-stacks \
		--stack-name recruiting-tool \
		--query 'Stacks[0].Outputs' \
		--output table

# Get the API key value
api-key:
	@aws apigateway get-api-keys \
		--include-values \
		--query 'items[?starts_with(name, `recruiting-tool`)].value' \
		--output text

# Tail logs for a specific function
logs-%:
	sam logs -n $*Function --stack-name recruiting-tool --tail

# Delete the stack
clean:
	sam delete --stack-name recruiting-tool --no-prompts
