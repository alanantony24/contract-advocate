from datetime import date, timedelta

from . import dynamo, bedrock_client

ESCALATION_CAP = 3  # hard cap regardless of what the model "wants" - never loop forever
DAYS_BETWEEN_ESCALATIONS = 7  # tune as needed; short for easier demoing


def process_case(case: dict, today: date = None) -> dict:
    """Looks at a single case's obligations and decides what, if anything,
    should happen today. This is the core 'plans, acts, adapts over time'
    logic - it's intentionally a plain function, not an agent framework, so
    it's easy to reason about and debug.

    Returns the updated case dict (also persists the update to DynamoDB).
    """
    today = today or date.today()
    case_id = case["case_id"]
    escalation_stage = case.get("escalation_stage", 0)
    message_history = list(case.get("message_history", []))
    obligations = case.get("obligations", [])
    action_taken = None

    for obligation in obligations:
        if obligation.get("type") != "payment_due":
            continue  # only payment obligations get the chase/escalate treatment for now
        if obligation.get("status") == "RESOLVED":
            continue
        if not obligation.get("date"):
            continue

        due_date = date.fromisoformat(obligation["date"])
        days_overdue = (today - due_date).days
        if days_overdue < 0:
            continue  # not due yet, nothing to do

        last_action = date.fromisoformat(case.get("last_action_date", today.isoformat()))
        days_since_last_action = (today - last_action).days

        should_act = (
            (escalation_stage == 0) or
            (escalation_stage > 0 and days_since_last_action >= DAYS_BETWEEN_ESCALATIONS)
        )

        if should_act and escalation_stage <= ESCALATION_CAP:
            message_text = bedrock_client.draft_followup_message(
                obligation, escalation_stage, message_history
            )
            message_history.append({
                "date": today.isoformat(),
                "type": f"escalation_stage_{escalation_stage}",
                "content": message_text,
            })
            escalation_stage += 1
            obligation["status"] = "REMINDED" if escalation_stage == 1 else "ESCALATED"
            action_taken = message_text

    new_status = case["status"]
    if action_taken:
        new_status = "REMINDER_SENT" if escalation_stage == 1 else f"ESCALATED_{escalation_stage - 1}"

    updates = {
        "status": new_status,
        "escalation_stage": escalation_stage,
        "message_history": message_history,
        "obligations": obligations,
        "last_action_date": today.isoformat() if action_taken else case.get("last_action_date"),
    }
    dynamo.update_case(case_id, updates)
    case.update(updates)
    return case


def advance_time(case_id: str, days: int) -> dict:
    """DEMO/DEBUG ONLY - simulates `days` passing so we can demo the escalation
    flow in a 5-minute video without waiting for real time to elapse. This is
    not a real product feature; don't expose it outside the demo build."""
    case = dynamo.get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    simulated_today = date.today() + timedelta(days=days)
    return process_case(case, today=simulated_today)


def run_daily_check() -> list:
    """Meant to be triggered once a day by EventBridge Scheduler. Processes
    every open (non-RESOLVED) case."""
    results = []
    for case in dynamo.list_open_cases():
        results.append(process_case(case))
    return results
