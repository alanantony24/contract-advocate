import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import state_machine


def lambda_handler(event, context):
    """DEMO/DEBUG ONLY. Not a real product feature - lets us show the
    escalation flow in a 5-minute video without waiting for real days to pass.
    Expects: {"days": 20}"""
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    http_method = event.get("httpMethod") or http_context.get("method")
    if http_method == "OPTIONS":
        return _response(200, {"ok": True})

    body = {}
    raw_body = event.get("body")
    if raw_body:
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

    case_id = _get_case_id(event, body)
    days = body.get("days", 1)

    if not case_id:
        return _response(400, {"error": "case_id is required"})

    try:
        updated_case = state_machine.advance_time(case_id, days)
        return _response(200, updated_case)
    except ValueError as e:
        return _response(404, {"error": str(e)})


def _get_case_id(event, body):
    params = event.get("pathParameters") or {}
    if "case_id" in params and params["case_id"]:
        return params["case_id"]
    qs = event.get("queryStringParameters") or {}
    if "case_id" in qs and qs["case_id"]:
        return qs["case_id"]
    if isinstance(body, dict) and body.get("case_id"):
        return body["case_id"]
    raw_path = event.get("rawPath") or ""
    parts = [p for p in raw_path.strip("/").split("/") if p and p not in ("cases", "advance-time", "advance_time")]
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
