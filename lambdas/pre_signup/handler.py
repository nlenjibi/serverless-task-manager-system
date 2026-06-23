import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Auto-confirm Cognito users and verify their email without a confirmation step."""
    logger.info("PreSignUp trigger: auto-confirming user %s", event.get("userName"))

    event["response"]["autoConfirmUser"] = True
    event["response"]["autoVerifyEmail"] = True

    return event
