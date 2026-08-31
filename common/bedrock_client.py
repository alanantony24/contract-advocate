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
    response = client.converse(
        modelId=config.BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        system=[{"text": system}],
        inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
    )
    return response["output"]["message"]["content"][0]["text"]


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
    return ask_bedrock(prompt, system=MESSAGE_DRAFT_SYSTEM_PROMPT, max_tokens=400, temperature=0.3)
