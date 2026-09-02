import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import dynamo


def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _response(200, {"ok": True})

    params = event.get("pathParameters") or {}
    case_id = params.get("case_id")
    if not case_id:
        return _response(400, {"error": "case_id is required"})

    case = dynamo.get_case(case_id)
    if not case:
        return _response(404, {"error": "case not found"})

    events = [{"date": case["last_action_date"], "type": "STATUS", "detail": case["status"]}]
    events += case.get("message_history", [])
    events.sort(key=lambda e: e.get("date", ""))

    return _response(200, {"case_id": case_id, "events": events})


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
