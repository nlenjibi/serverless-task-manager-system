from botocore.exceptions import ClientError

from lib.ddb import table
from lib.http import respond, get_user_id
from lib.observability import logger, tracer


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
        task_id = event["pathParameters"]["taskId"]

        table.delete_item(
            Key={"UserId": user_id, "TaskId": task_id},
            ConditionExpression="attribute_exists(TaskId) AND UserId = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )

        logger.info("Deleted task %s for user %s", task_id, user_id)
        return respond(200, {"message": "Task deleted successfully", "taskId": task_id})

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return respond(404, {"message": "Task not found"})
        logger.exception("AWS error deleting task")
        return respond(500, {"message": str(exc)})
    except Exception:
        logger.exception("Unexpected error deleting task")
        return respond(500, {"message": "Internal server error"})
