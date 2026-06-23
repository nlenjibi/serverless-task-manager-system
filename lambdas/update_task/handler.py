import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TASKS_TABLE"]
table = dynamodb.Table(TABLE_NAME)

CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}

MUTABLE_STATUSES = {"Pending", "Completed"}


def _response(status: int, body) -> dict:
    return {"statusCode": status, "headers": CORS, "body": json.dumps(body)}


def lambda_handler(event, context):
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        task_id = event["pathParameters"]["taskId"]
        body = json.loads(event.get("body") or "{}")

        set_clauses = ["UpdatedAt = :updated"]
        expr_values = {":updated": datetime.now(timezone.utc).isoformat()}
        expr_names = {}

        if "description" in body:
            set_clauses.append("Description = :desc")
            expr_values[":desc"] = body["description"]

        if "date" in body:
            set_clauses.append("#dt = :date")
            expr_values[":date"] = body["date"]
            expr_names["#dt"] = "Date"

        if "status" in body and body["status"] in MUTABLE_STATUSES:
            set_clauses.append("#st = :status")
            expr_values[":status"] = body["status"]
            expr_names["#st"] = "Status"

        update_expr = "SET " + ", ".join(set_clauses)

        kwargs = {
            "Key": {"UserId": user_id, "TaskId": task_id},
            "UpdateExpression": update_expr,
            "ConditionExpression": "attribute_exists(TaskId) AND UserId = :uid",
            "ExpressionAttributeValues": {":uid": user_id, **expr_values},
            "ReturnValues": "ALL_NEW",
        }
        if expr_names:
            kwargs["ExpressionAttributeNames"] = expr_names

        result = table.update_item(**kwargs)
        logger.info("Updated task %s for user %s", task_id, user_id)
        return _response(200, result["Attributes"])

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(404, {"error": "Task not found"})
        logger.error("AWS error: %s", exc)
        return _response(500, {"error": str(exc)})
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        return _response(500, {"error": "Internal server error"})
