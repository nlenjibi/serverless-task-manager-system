import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

from lib.ddb import table
from lib.http import respond, get_user_id
from lib.observability import logger, tracer

scheduler = boto3.client("scheduler")

SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]
EXPIRY_FUNCTION_ARN = os.environ["EXPIRY_FUNCTION_ARN"]

DEFAULT_DEADLINE_MINUTES = 5


def _resolve_deadline(now: datetime, requested: str | None) -> datetime:
    """Uses the client-supplied deadline if it parses and is in the future,
    otherwise falls back to the default of now + 5 minutes."""
    if requested:
        try:
            parsed = datetime.fromisoformat(requested.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed > now:
                return parsed
        except ValueError:
            logger.warning("Ignoring unparsable deadline %r", requested)
    return now + timedelta(minutes=DEFAULT_DEADLINE_MINUTES)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
def lambda_handler(event, context):
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        user_id = get_user_id(event)
        user_email = claims.get("email", "")

        body = json.loads(event.get("body") or "{}")

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        deadline_dt = _resolve_deadline(now, body.get("deadline"))

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

        return respond(201, task)

    except ClientError as exc:
        logger.exception("AWS error creating task")
        return respond(500, {"message": str(exc)})
    except Exception:
        logger.exception("Unexpected error creating task")
        return respond(500, {"message": "Internal server error"})
