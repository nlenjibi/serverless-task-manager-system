import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def _already_subscribed(email: str) -> bool:
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=SNS_TOPIC_ARN):
        for sub in page["Subscriptions"]:
            if sub["Protocol"] == "email" and sub["Endpoint"] == email:
                return True
    return False


def lambda_handler(event, context):
    """Subscribe the authenticated user's email to the SNS topic (once)."""
    user_attrs = event["request"]["userAttributes"]
    email = user_attrs.get("email", "")
    user_id = event["userName"]

    logger.info("PostAuthentication for user %s (%s)", user_id, email)

    if not email:
        logger.warning("No email attribute found for user %s — skipping SNS subscribe", user_id)
        return event

    if _already_subscribed(email):
        logger.info("User %s already subscribed — skipping", email)
        return event

    try:
        sns.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
            Attributes={
                # Filter policy ensures the user only receives their own task notifications
                "FilterPolicy": json.dumps({"userId": [user_id]})
            },
        )
        logger.info("Subscribed %s to SNS topic", email)
    except ClientError as exc:
        logger.error("Failed to subscribe %s: %s", email, exc)

    return event
