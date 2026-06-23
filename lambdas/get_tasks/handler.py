import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key

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

        result = table.query(KeyConditionExpression=Key("UserId").eq(user_id))
        tasks = result.get("Items", [])

        # Paginate through all results if the table returns more than one page
        while "LastEvaluatedKey" in result:
            result = table.query(
                KeyConditionExpression=Key("UserId").eq(user_id),
                ExclusiveStartKey=result["LastEvaluatedKey"],
            )
            tasks.extend(result.get("Items", []))

        logger.info("Retrieved %d tasks for user %s", len(tasks), user_id)
        return _response(200, tasks)

    except Exception as exc:
        logger.error("Error fetching tasks: %s", exc)
        return _response(500, {"error": "Internal server error"})
