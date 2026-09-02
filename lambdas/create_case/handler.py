import json
import base64
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import pdf_utils, bedrock_client, dynamo


def lambda_handler(event, context):
    """Expects a JSON body: {"user_id": "...", "pdf_base64": "..."}"""
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    http_method = event.get("httpMethod") or http_context.get("method")
    if http_method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id", "demo-user")
        pdf_b64 = body["pdf_base64"]
        pdf_bytes = base64.b64decode(pdf_b64)

        contract_text = pdf_utils.extract_text_from_pdf_bytes(pdf_bytes)
        if not contract_text.strip():
            return _response(400, {
                "error": "Could not extract text from PDF. Is it a scanned/image PDF? "
                         "Those aren't supported yet - try a text-based PDF."
            })

        case = dynamo.create_case(user_id)
        extracted = bedrock_client.extract_contract_json(contract_text)

        dynamo.update_case(case["case_id"], {
            "status": "EXTRACTED",
            "clauses_flagged": extracted.get("clauses_flagged", []),
            "obligations": [
                {**o, "status": "PENDING"} for o in extracted.get("obligations", [])
            ],
        })

        return _response(200, {"case_id": case["case_id"], "status": "EXTRACTED"})
    except KeyError as e:
        return _response(400, {"error": f"Missing required field: {e}"})
    except Exception as e:
        return _response(500, {"error": str(e)})


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
