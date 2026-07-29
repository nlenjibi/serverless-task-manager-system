from boto3.dynamodb.conditions import Key

from lib.ddb import table
from lib.http import respond, get_user_id
from lib.observability import logger, tracer


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)

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
        return respond(200, tasks)

    except Exception:
        logger.exception("Error fetching tasks")
        return respond(500, {"message": "Internal server error"})
