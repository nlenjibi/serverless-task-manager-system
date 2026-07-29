import os

import boto3

TABLE_NAME = os.environ["TASKS_TABLE"]

_dynamodb = boto3.resource("dynamodb")
table = _dynamodb.Table(TABLE_NAME)
