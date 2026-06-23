import json
import logging
import os

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


def _response(status: int, body) -> dict:
    return {"statusCode": status, "headers": CORS, "body": json.dumps(body)}


def lambda_handler(event, context):
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        task_id = event["pathParameters"]["taskId"]

        table.delete_item(
            Key={"UserId": user_id, "TaskId": task_id},
            ConditionExpression="attribute_exists(TaskId) AND UserId = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )

        logger.info("Deleted task %s for user %s", task_id, user_id)
        return _response(200, {"message": "Task deleted successfully", "taskId": task_id})

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(404, {"error": "Task not found"})
        logger.error("AWS error: %s", exc)
        return _response(500, {"error": str(exc)})
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        return _response(500, {"error": "Internal server error"})
