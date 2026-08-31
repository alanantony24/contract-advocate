import uuid
from datetime import date

import boto3
from boto3.dynamodb.conditions import Attr

from . import config

_resource = None


def get_table():
    global _resource
    if _resource is None:
        _resource = boto3.resource("dynamodb", region_name=config.AWS_REGION)
    return _resource.Table(config.DYNAMODB_TABLE)


def create_case(user_id: str) -> dict:
    case = {
        "case_id": str(uuid.uuid4()),
        "user_id": user_id,
        "status": "PROCESSING",
        "clauses_flagged": [],
        "obligations": [],
        "escalation_stage": 0,
        "last_action_date": date.today().isoformat(),
        "message_history": [],
    }
    get_table().put_item(Item=case)
    return case


def get_case(case_id: str):
    resp = get_table().get_item(Key={"case_id": case_id})
    return resp.get("Item")


def update_case(case_id: str, updates: dict) -> None:
    """Simple full-field update helper - fine for hackathon scale (no concurrent
    writers on the same case). Skips any keys with a value of None so callers
    can pass a dict without worrying about accidentally clearing fields."""
    updates = {k: v for k, v in updates.items() if v is not None}
    if not updates:
        return

    expr_names = {}
    expr_values = {}
    set_clauses = []
    for i, (k, v) in enumerate(updates.items()):
        name_key = f"#f{i}"
        value_key = f":v{i}"
        expr_names[name_key] = k
        expr_values[value_key] = v
        set_clauses.append(f"{name_key} = {value_key}")

    get_table().update_item(
        Key={"case_id": case_id},
        UpdateExpression="SET " + ", ".join(set_clauses),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def append_message(case_id: str, message: dict) -> None:
    case = get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    history = case.get("message_history", [])
    history.append(message)
    update_case(case_id, {"message_history": history})


def list_open_cases() -> list:
    """Scan for cases that aren't RESOLVED. Fine at hackathon scale/data volume;
    would need a GSI on `status` at real scale to avoid a full table scan."""
    resp = get_table().scan(FilterExpression=Attr("status").ne("RESOLVED"))
    return resp.get("Items", [])
