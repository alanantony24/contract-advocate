"""
Runs the whole flow locally, without deploying anything to Lambda yet:
extract -> confirm -> simulate time passing -> see escalation messages get drafted.

Before running this:
1. Fill in .env with your AWS credentials (copy from .env.example)
2. Run: python scripts/setup_dynamodb.py   (creates the DynamoDB table, once)
3. Confirm Bedrock access works: python test_bedrock.py

Usage (from the project root):
    python scripts/run_local_demo.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import bedrock_client, dynamo, state_machine


def main():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "tests", "sample_contract.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        contract_text = f.read()

    print("== Step 1: Extracting clauses + obligations from the sample contract ==")
    extracted = bedrock_client.extract_contract_json(contract_text)
    print(json.dumps(extracted, indent=2))

    print("\n== Step 2: Creating case in DynamoDB ==")
    case = dynamo.create_case(user_id="demo-user")
    dynamo.update_case(case["case_id"], {
        "status": "EXTRACTED",
        "clauses_flagged": extracted.get("clauses_flagged", []),
        "obligations": [{**o, "status": "PENDING"} for o in extracted.get("obligations", [])],
    })
    print(f"Created case: {case['case_id']}")

    print("\n== Step 3: Confirming case (starts tracking) ==")
    dynamo.update_case(case["case_id"], {"status": "AWAITING_PAYMENT"})

    print("\n== Step 4: Simulating time passing until the payment is overdue ==")
    updated = state_machine.advance_time(case["case_id"], days=25)
    print(f"New status: {updated['status']}")
    _print_messages(updated)

    print("\n== Step 5: Simulating more time passing (further escalation) ==")
    updated = state_machine.advance_time(case["case_id"], days=35)
    print(f"New status: {updated['status']}")
    _print_messages(updated)

    print(f"\nDone. Case ID for reference: {case['case_id']}")


def _print_messages(case):
    for m in case.get("message_history", []):
        print(f"  [{m['date']}] {m['type']}:\n    {m['content']}\n")


if __name__ == "__main__":
    main()
