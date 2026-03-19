"""Health check handler."""

import os
import boto3
from src.utils.response import success, error


def check(event, context):
    """GET /health — Verify API and DynamoDB connectivity."""
    try:
        client = boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("TABLE_NAME", "recruiting-candidates")
        response = client.describe_table(TableName=table_name)
        table_status = response["Table"]["TableStatus"]
        return success({
            "status": "healthy",
            "table": table_name,
            "table_status": table_status,
        })
    except Exception as e:
        return error(f"unhealthy: {e}", status_code=503)
