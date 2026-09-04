import logging
import os
import json
import boto3
from . import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_sns_client = None
_ses_client = None


def _get_sns():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client("sns", region_name=config.AWS_REGION)
    return _sns_client


def _get_ses():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses", region_name=config.AWS_REGION)
    return _ses_client


def send_overdue_alert(case: dict, obligation: dict, stage: int, message_text: str, app_url: str = "https://alanantony24.github.io/contract-advocate") -> dict:
    """Dispatches a multi-channel notification to the freelancer (via AWS SNS / SES)
    when a contract obligation is overdue.

    Includes the direct deep-link so the freelancer can open the app, review the
    Bedrock-drafted message, and copy/send it to the client.
    """
    case_id = case.get("case_id", "")
    client_name = obligation.get("party_responsible", "Client")
    amount = obligation.get("amount", "3000")
    due_date = obligation.get("date", "N/A")
    deep_link = f"{app_url}/?case_id={case_id}"

    stage_names = {
        0: "Polite Reminder",
        1: "Firm Follow-Up",
        2: "Small-Claims Final Notice",
        3: "Legal Demand"
    }
    stage_name = stage_names.get(stage, f"Stage {stage} Escalation")

    subject = f"[Contract Advocate] Payment Overdue Alert: {client_name} (${amount} SGD)"
    body = (
        f"⚡ CONTRACT ADVOCATE ALERT\n\n"
        f"Client: {client_name}\n"
        f"Due Date: {due_date}\n"
        f"Amount: ${amount} SGD\n"
        f"Status: Payment overdue ({stage_name})\n\n"
        f"Our Amazon Bedrock AI Agent has autonomously prepared an escalated follow-up communication for you:\n\n"
        f"----------------------------------------\n"
        f"{message_text}\n"
        f"----------------------------------------\n\n"
        f"👉 Click here to review in your Tracker and copy the message:\n"
        f"{deep_link}\n"
    )

    result = {
        "status": "DISPATCHED",
        "deep_link": deep_link,
        "subject": subject,
        "body": body,
        "channels": []
    }

    # 1. Dispatch via AWS SNS (SMS / Topic) if configured
    sns_topic_arn = os.getenv("SNS_TOPIC_ARN")
    if sns_topic_arn:
        try:
            sns = _get_sns()
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject=subject,
                Message=body
            )
            result["channels"].append("AWS_SNS_TOPIC")
            logger.info("Alert published to SNS Topic: %s", sns_topic_arn)
        except Exception as e:
            logger.warning("SNS publish failed: %s", e)

    # 2. Dispatch via AWS SES (Email) if configured
    ses_sender = os.getenv("SES_SENDER_EMAIL")
    user_email = case.get("user_email") or os.getenv("DEFAULT_USER_EMAIL")
    if ses_sender and user_email:
        try:
            ses = _get_ses()
            ses.send_email(
                Source=ses_sender,
                Destination={"ToAddresses": [user_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )
            result["channels"].append("AWS_SES_EMAIL")
            logger.info("Alert emailed via SES to: %s", user_email)
        except Exception as e:
            logger.warning("SES send failed: %s", e)

    logger.info("Overdue alert prepared for case %s: %s", case_id, json.dumps(result))
    return result
