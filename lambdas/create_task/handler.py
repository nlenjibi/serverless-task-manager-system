import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
scheduler = boto3.client("scheduler")

TABLE_NAME = os.environ["TASKS_TABLE"]
SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]
EXPIRY_FUNCTION_ARN = os.environ["EXPIRY_FUNCTION_ARN"]

table = dynamodb.Table(TABLE_NAME)

CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}

DEADLINE_MINUTES = 5


def _response(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": CORS, "body": json.dumps(body)}


def lambda_handler(event, context):
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        user_id = claims["sub"]
        user_email = claims.get("email", "")

        body = json.loads(event.get("body") or "{}")

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        deadline_dt = now + timedelta(minutes=DEADLINE_MINUTES)

        task = {
            "UserId": user_id,
            "TaskId": task_id,
            "Description": body.get("description", ""),
            "Date": body.get("date", now.strftime("%Y-%m-%d")),
            "Status": "Pending",
            "Deadline": deadline_dt.isoformat(),
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat(),
            "UserEmail": user_email,
        }

        table.put_item(Item=task)
        logger.info("Created task %s for user %s", task_id, user_id)

        # Schedule a one-time EventBridge Scheduler event at the deadline
        schedule_name = f"task-expiry-{task_id}"
        scheduler.create_schedule(
            Name=schedule_name,
            GroupName="default",
            ScheduleExpression=f"at({deadline_dt.strftime('%Y-%m-%dT%H:%M:%S')})",
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": EXPIRY_FUNCTION_ARN,
                "RoleArn": SCHEDULER_ROLE_ARN,
                "Input": json.dumps({"taskId": task_id, "userId": user_id}),
            },
            ActionAfterCompletion="DELETE",
        )
        logger.info("Created expiry schedule %s", schedule_name)

        return _response(201, task)

    except ClientError as exc:
        logger.error("AWS error: %s", exc)
        return _response(500, {"error": str(exc)})
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        return _response(500, {"error": "Internal server error"})
