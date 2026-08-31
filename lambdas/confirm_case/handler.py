import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import dynamo


def lambda_handler(event, context):
    params = event.get("pathParameters") or {}
    case_id = params.get("case_id")
    body = json.loads(event.get("body", "{}"))

    if not case_id:
        return _response(400, {"error": "case_id is required"})

    case = dynamo.get_case(case_id)
    if not case:
        return _response(404, {"error": "case not found"})

    # Let the user correct anything the extraction got wrong (e.g. a misread
    # due date) before tracking starts - matches the human-in-the-loop pattern.
    obligations = body.get("obligations", case.get("obligations", []))

    dynamo.update_case(case_id, {
        "status": "AWAITING_PAYMENT",
        "obligations": obligations,
        "last_action_date": date.today().isoformat(),
    })
    return _response(200, {"status": "AWAITING_PAYMENT"})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict, default=str),
    }
