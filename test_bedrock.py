"""Run this first, before anything else, to confirm your AWS credentials and
Bedrock model access are working.

Usage (from the project root, with .env filled in):
    python test_bedrock.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from common import bedrock_client

if __name__ == "__main__":
    result = bedrock_client.ask_bedrock("Say hello in one sentence.")
    print(result)
