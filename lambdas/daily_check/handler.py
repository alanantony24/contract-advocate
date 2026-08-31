import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import state_machine


def lambda_handler(event, context):
    """Triggered by EventBridge Scheduler once a day. No meaningful input
    event - it just checks every open case and acts where needed."""
    results = state_machine.run_daily_check()
    return {"processed_cases": len(results)}
