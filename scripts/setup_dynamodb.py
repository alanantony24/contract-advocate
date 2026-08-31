"""Run once to create the DynamoDB table. Safe to re-run - it just skips
creation if the table already exists.

Usage (from the project root, with your .env filled in):
    python scripts/setup_dynamodb.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3
from common import config


def main():
    client = boto3.client("dynamodb", region_name=config.AWS_REGION)
    try:
        client.create_table(
            TableName=config.DYNAMODB_TABLE,
            KeySchema=[{"AttributeName": "case_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "case_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",  # on-demand, never provisioned capacity
        )
        print(f"Creating table '{config.DYNAMODB_TABLE}'... this can take a few seconds. "
              f"Check the DynamoDB console to confirm it's ACTIVE before running the demo.")
    except client.exceptions.ResourceInUseException:
        print(f"Table '{config.DYNAMODB_TABLE}' already exists - skipping.")


if __name__ == "__main__":
    main()
