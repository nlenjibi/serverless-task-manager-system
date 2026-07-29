import json

import boto3
from botocore.exceptions import ClientError

from lib.observability import logger, tracer

scheduler = boto3.client("scheduler")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
def lambda_handler(event, context):
    """
    Reads cancellation messages from the SQS FIFO queue and deletes the
    corresponding EventBridge Scheduler one-time schedule.
    Uses ReportBatchItemFailures so SQS only retries truly failed messages.
    """
    failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        schedule_name = None
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
                logger.exception("Failed to delete schedule %s", schedule_name)
                failures.append({"itemIdentifier": message_id})

        except Exception:
            logger.exception("Unexpected error for message %s", message_id)
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
