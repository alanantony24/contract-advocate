import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import state_machine


def lambda_handler(event, context):
    """DEMO/DEBUG ONLY. Not a real product feature - lets us show the
    escalation flow in a 5-minute video without waiting for real days to pass.
    Expects: {"days": 20}"""
    params = event.get("pathParameters") or {}
    case_id = params.get("case_id")
    body = json.loads(event.get("body", "{}"))
    days = body.get("days", 1)

    if not case_id:
        return _response(400, {"error": "case_id is required"})

    try:
        updated_case = state_machine.advance_time(case_id, days)
        return _response(200, updated_case)
    except ValueError as e:
        return _response(404, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict, default=str),
    }
