import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import dynamo


def lambda_handler(event, context):
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    http_method = event.get("httpMethod") or http_context.get("method")
    if http_method == "OPTIONS":
        return _response(200, {"ok": True})

    case_id = _get_case_id(event)
    if not case_id:
        return _response(400, {"error": "case_id is required"})

    case = dynamo.get_case(case_id)
    if not case:
        return _response(404, {"error": "case not found"})

    return _response(200, case)


def _get_case_id(event):
    params = event.get("pathParameters") or {}
    if "case_id" in params and params["case_id"]:
        return params["case_id"]
    qs = event.get("queryStringParameters") or {}
    if "case_id" in qs and qs["case_id"]:
        return qs["case_id"]
    # Fallback to rawPath e.g. /cases/abc123 or /abc123
    raw_path = event.get("rawPath") or ""
    parts = [p for p in raw_path.strip("/").split("/") if p and p != "cases"]
    if parts:
        return parts[0]
    return None


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body_dict, default=str),
    }
