import json
import boto3
from . import config

_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    return _client


def ask_bedrock(prompt: str, system: str = "You are a helpful assistant.",
                 max_tokens: int = 1000, temperature: float = 0.0) -> str:
    client = get_client()
    model_ids = [
        config.BEDROCK_MODEL_ID,
        "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "us.anthropic.claude-3-haiku-20240307-v1:0",
    ]
    last_err = None
    for mid in model_ids:
        try:
            response = client.converse(
                modelId=mid,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=[{"text": system}],
                inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
            )
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            last_err = e
            continue
    raise last_err or RuntimeError("Failed to invoke Bedrock model")


EXTRACTION_SYSTEM_PROMPT = """You are a contract analysis assistant. You read freelance/contractor
agreements and extract two things:

1. Clauses that could be risky or unusual for the person signing (the contractor/freelancer),
   with a plain-English explanation of why.
2. Every date-bound obligation in the contract - not just payment. Include renewal notice
   windows, deliverable deadlines, termination notice windows, and payment due dates.

You must respond with ONLY valid JSON, no preamble, no markdown code fences, no explanation
outside the JSON. If a date is relative (e.g. "30 days after signing") resolve it to an actual
YYYY-MM-DD date using the signing date given in the contract as the anchor. If you truly cannot
determine a date, use null.

Output exactly this JSON shape:
{
  "clauses_flagged": [
    {"clause_text": "...", "risk_level": "low|medium|high", "reason": "..."}
  ],
  "obligations": [
    {"type": "payment_due|renewal_notice|deliverable_due|termination_window",
     "date": "YYYY-MM-DD or null",
     "amount": null,
     "party_responsible": "user|client",
     "description": "..."}
  ]
}
"""


def extract_contract_json(contract_text: str, max_retries: int = 2) -> dict:
    """Calls Bedrock to extract clauses + obligations from contract text.

    Retries with a stricter reminder if the model doesn't return valid JSON -
    this is the single highest-leverage piece of the whole project, so it's
    worth the extra robustness here.
    """
    prompt = f"Analyze this contract:\n\n{contract_text}"
    last_error = None

    for _ in range(max_retries + 1):
        raw = ask_bedrock(prompt, system=EXTRACTION_SYSTEM_PROMPT, max_tokens=2000)
        cleaned = _strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = e
            prompt = (
                f"Analyze this contract:\n\n{contract_text}\n\n"
                f"IMPORTANT: Your previous response was not valid JSON. "
                f"Respond with ONLY the JSON object, nothing else - no markdown fences, "
                f"no commentary."
            )

    raise ValueError(f"Bedrock did not return valid JSON after {max_retries + 1} attempts: {last_error}")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


MESSAGE_DRAFT_SYSTEM_PROMPT = """You are drafting a follow-up message on behalf of a freelancer
who is owed payment or facing another contractual deadline. Keep the tone professional.

Escalate firmness gradually based on the escalation_stage provided:
- 0: friendly reminder, assume it may have been an oversight
- 1: firmer follow-up, reference the original due date explicitly
- 2 or higher: final notice, reference that the freelancer is considering next steps
  such as small claims, but stay professional and factual, not threatening

Do not repeat previous messages verbatim - briefly reference them if relevant so the
message history reads as a coherent, escalating thread. Respond with ONLY the message
text, no preamble, no subject line unless natural for an email.
"""


def draft_followup_message(obligation: dict, escalation_stage: int, message_history: list) -> str:
    history_text = "\n".join(
        f"- [{m.get('date')}] {m.get('type')}: {m.get('content')}" for m in message_history
    ) or "(no previous messages)"

    prompt = (
        f"Obligation: {json.dumps(obligation, default=str)}\n"
        f"Escalation stage: {escalation_stage}\n"
        f"Message history so far:\n{history_text}\n\n"
        f"Draft the next follow-up message."
    )
    try:
        return ask_bedrock(prompt, system=MESSAGE_DRAFT_SYSTEM_PROMPT, max_tokens=400, temperature=0.3)
    except Exception as e:
        # Fallback template if Bedrock is temporarily unavailable
        client_name = obligation.get("party_responsible", "Client")
        amount = obligation.get("amount", "3000")
        due_date = obligation.get("date", "agreed date")
        desc = obligation.get("description", "Contract Payment")
        if escalation_stage == 0:
            return (
                f"Hi {client_name},\n\n"
                f"I hope you are doing well. Just a polite reminder regarding the payment for '{desc}' "
                f"in the amount of ${amount} SGD, which was due on {due_date}.\n\n"
                f"Please let me know if you need any additional invoice details or confirmation.\n\n"
                f"Best regards."
            )
        elif escalation_stage == 1:
            return (
                f"Dear {client_name},\n\n"
                f"I am writing to follow up on my previous message regarding the outstanding invoice for '{desc}' "
                f"(${amount} SGD), which was scheduled for payment on {due_date}.\n\n"
                f"As the invoice is now overdue, could you please provide an update on when payment will be processed?\n\n"
                f"Thank you for your prompt attention."
            )
        else:
            return (
                f"Formal Notice: Outstanding Payment of ${amount} SGD for '{desc}'\n\n"
                f"Dear {client_name},\n\n"
                f"Despite previous reminders, the invoice due on {due_date} remains unpaid. "
                f"Please arrange for immediate settlement within 5 business days. If payment is not received, "
                f"I will have no choice but to escalate this matter through formal dispute resolution channels, "
                f"including the Small Claims Tribunals.\n\n"
                f"Sincerely."
            )
