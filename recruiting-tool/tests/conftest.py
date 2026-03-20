"""Shared test fixtures — mocked DynamoDB table for handler integration tests."""

import json
import os
import pytest
import boto3
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Set required env vars for all tests."""
    monkeypatch.setenv("TABLE_NAME", "recruiting-candidates")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")  # disable Slack in tests
    monkeypatch.setenv("ASSETS_BUCKET", "test-assets")


@pytest.fixture
def dynamodb_table():
    """Create a mocked DynamoDB table matching our SAM template."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="recruiting-candidates",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield client


def api_event(method="GET", path="/", body=None, path_params=None, query_params=None):
    """Build a fake API Gateway event."""
    event = {
        "httpMethod": method,
        "path": path,
        "pathParameters": path_params,
        "queryStringParameters": query_params,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if body else None,
    }
    return event
