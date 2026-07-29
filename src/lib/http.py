import json

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def respond(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, default=str),
    }


def get_user_id(event: dict) -> str:
    """Cognito's API Gateway authorizer puts the validated JWT's `sub` claim
    into requestContext.authorizer.claims once the token has been verified."""
    claims = (event.get("requestContext") or {}).get("authorizer", {}).get("claims") or {}
    user_id = claims.get("sub")
    if not user_id:
        raise ValueError("Missing Cognito authorizer claims on request")
    return user_id
