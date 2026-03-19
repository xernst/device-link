"""DynamoDB service for CRUD operations."""

import os
from datetime import datetime, timezone
from typing import Optional

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "recruiting-candidates")


def _get_table():
    dynamodb = boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return dynamodb


def put_item(item: dict) -> dict:
    """Put an item into the table."""
    client = _get_table()
    return client.put_item(TableName=TABLE_NAME, Item=item)


def get_item(pk: str, sk: str) -> Optional[dict]:
    """Get a single item by PK and SK."""
    client = _get_table()
    response = client.get_item(
        TableName=TABLE_NAME,
        Key={"PK": {"S": pk}, "SK": {"S": sk}},
    )
    return response.get("Item")


def query_by_pk(pk: str, sk_prefix: Optional[str] = None) -> list:
    """Query items by partition key with optional sort key prefix."""
    client = _get_table()
    params = {
        "TableName": TABLE_NAME,
        "KeyConditionExpression": "PK = :pk",
        "ExpressionAttributeValues": {":pk": {"S": pk}},
    }
    if sk_prefix:
        params["KeyConditionExpression"] += " AND begins_with(SK, :sk)"
        params["ExpressionAttributeValues"][":sk"] = {"S": sk_prefix}
    response = client.query(**params)
    return response.get("Items", [])


def query_gsi1(gsi1pk: str, gsi1sk_prefix: Optional[str] = None) -> list:
    """Query the GSI1 index."""
    client = _get_table()
    params = {
        "TableName": TABLE_NAME,
        "IndexName": "GSI1",
        "KeyConditionExpression": "GSI1PK = :pk",
        "ExpressionAttributeValues": {":pk": {"S": gsi1pk}},
    }
    if gsi1sk_prefix:
        params["KeyConditionExpression"] += " AND begins_with(GSI1SK, :sk)"
        params["ExpressionAttributeValues"][":sk"] = {"S": gsi1sk_prefix}
    response = client.query(**params)
    return response.get("Items", [])


def delete_item(pk: str, sk: str) -> dict:
    """Delete an item by PK and SK."""
    client = _get_table()
    return client.delete_item(
        TableName=TABLE_NAME,
        Key={"PK": {"S": pk}, "SK": {"S": sk}},
    )


def update_status(pk: str, sk: str, new_status: str, gsi1sk_prefix: str = "") -> dict:
    """Update the status field and GSI1SK of an item."""
    client = _get_table()
    now = datetime.now(timezone.utc).isoformat()
    # Extract the ID portion from the existing GSI1SK for reconstruction
    params = {
        "TableName": TABLE_NAME,
        "Key": {"PK": {"S": pk}, "SK": {"S": sk}},
        "UpdateExpression": "SET #status = :status, updated_at = :now",
        "ExpressionAttributeNames": {"#status": "status"},
        "ExpressionAttributeValues": {
            ":status": {"S": new_status},
            ":now": {"S": now},
        },
        "ReturnValues": "ALL_NEW",
    }
    return client.update_item(**params)
