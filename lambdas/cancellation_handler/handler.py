import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

scheduler = boto3.client("scheduler")


def lambda_handler(event, context):
    """
    Reads cancellation messages from the SQS FIFO queue and deletes the
    corresponding EventBridge Scheduler one-time schedule.
    Uses ReportBatchItemFailures so SQS only retries truly failed messages.
    """
    failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            task_id = body["taskId"]
            schedule_name = f"task-expiry-{task_id}"

            scheduler.delete_schedule(Name=schedule_name, GroupName="default")
            logger.info("Deleted expiry schedule %s", schedule_name)

        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ResourceNotFoundException":
                # Schedule already fired or was deleted — treat as success
                logger.info("Schedule not found (already fired or removed): %s", schedule_name)
            else:
                logger.error("Failed to delete schedule %s: %s", schedule_name, exc)
                failures.append({"itemIdentifier": message_id})

        except Exception as exc:
            logger.error("Unexpected error for message %s: %s", message_id, exc)
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
