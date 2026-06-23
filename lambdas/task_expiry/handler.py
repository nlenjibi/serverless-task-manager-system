import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TASKS_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Triggered by EventBridge Scheduler at the task deadline.
    Conditionally marks the task Expired (only if still Pending) then notifies the owner via SNS.
    """
    task_id = event["taskId"]
    user_id = event["userId"]

    logger.info("Expiry check for task %s (user %s)", task_id, user_id)

    try:
        result = table.update_item(
            Key={"UserId": user_id, "TaskId": task_id},
            UpdateExpression="SET #st = :expired, UpdatedAt = :updated",
            # Idempotent guard: only update if the task is still Pending
            ConditionExpression="#st = :pending AND attribute_exists(TaskId)",
            ExpressionAttributeNames={"#st": "Status"},
            ExpressionAttributeValues={
                ":expired": "Expired",
                ":pending": "Pending",
                ":updated": datetime.now(timezone.utc).isoformat(),
            },
            ReturnValues="ALL_NEW",
        )

        task = result["Attributes"]
        description = task.get("Description", "(no description)")
        deadline = task.get("Deadline", "unknown")

        logger.info("Task %s marked Expired", task_id)

        message = (
            f"Hello,\n\n"
            f"Your task has expired and was not completed by the deadline.\n\n"
            f"  Task: {description}\n"
            f"  Deadline: {deadline}\n"
            f"  Status: Expired\n\n"
            f"Log in to your Todo App to review your tasks."
        )

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="[Todo App] Task Expired",
            Message=message,
            # Filter policy matches the subscription created in PostAuthentication
            MessageAttributes={
                "userId": {
                    "DataType": "String",
                    "StringValue": user_id,
                }
            },
        )
        logger.info("SNS notification dispatched for task %s", task_id)

    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            logger.info("Task %s is no longer Pending — skipping expiry", task_id)
        else:
            logger.error("AWS error processing expiry for task %s: %s", task_id, exc)
            raise
