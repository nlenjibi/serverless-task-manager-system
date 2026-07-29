import json
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from lib.ddb import table
from lib.http import respond, get_user_id
from lib.observability import logger, tracer

MUTABLE_STATUSES = {"Pending", "Completed"}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
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
        return respond(200, result["Attributes"])

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return respond(404, {"message": "Task not found"})
        logger.exception("AWS error updating task")
        return respond(500, {"message": str(exc)})
    except Exception:
        logger.exception("Unexpected error updating task")
        return respond(500, {"message": "Internal server error"})
