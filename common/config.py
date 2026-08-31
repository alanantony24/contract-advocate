import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "Cases")
S3_BUCKET = os.getenv("S3_BUCKET", "contract-advocate-uploads")
