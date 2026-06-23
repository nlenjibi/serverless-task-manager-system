import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["CANCELLATION_QUEUE_URL"]


def _extract_str(image: dict, key: str) -> str:
    return image.get(key, {}).get("S", "")


def lambda_handler(event, context):
    """
    Consumes DynamoDB Stream events.
    When a task transitions from Pending → Completed, or is deleted while Pending,
    publishes a cancellation message to the SQS FIFO queue so the scheduled
    EventBridge Scheduler rule can be removed.
    """
    for record in event["Records"]:
        event_name = record["eventName"]
        ddb = record.get("dynamodb", {})
        new_image = ddb.get("NewImage", {})
        old_image = ddb.get("OldImage", {})

        task_id = _extract_str(new_image or old_image, "TaskId")
        user_id = _extract_str(new_image or old_image, "UserId")

        if not task_id or not user_id:
            continue

        old_status = _extract_str(old_image, "Status")
        new_status = _extract_str(new_image, "Status")

        should_cancel = (
            # Completed before deadline
            (event_name == "MODIFY" and old_status == "Pending" and new_status == "Completed")
            # Deleted while still Pending
            or (event_name == "REMOVE" and old_status == "Pending")
        )

        if not should_cancel:
            continue

        try:
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps({"taskId": task_id, "userId": user_id}),
                MessageGroupId=user_id,
                # Deduplication key prevents duplicate cancellations for the same task
                MessageDeduplicationId=f"{task_id}-cancel",
            )
            logger.info(
                "Queued cancellation for task %s (event: %s, %s → %s)",
                task_id,
                event_name,
                old_status,
                new_status,
            )
        except ClientError as exc:
            logger.error("Failed to queue cancellation for task %s: %s", task_id, exc)
            raise
