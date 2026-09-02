# Contract Advocate

An agent that reviews a freelance contract for risky clauses and date-bound
obligations (payment due, renewal notice, deliverable deadlines, termination
windows), then tracks those obligations over time - drafting and escalating
follow-up messages if a payment isn't made by its due date.

Built for the IGNITE Agentic AI Hackathon 2026. Everything runs on-demand /
serverless to stay within the AWS sandbox budget: Bedrock (on-demand only),
Lambda, DynamoDB (on-demand capacity), S3, EventBridge Scheduler. No
OpenSearch, no SageMaker endpoints, no EC2/RDS, no NAT/load balancers.

## Project structure

```
contract-advocate/
├── common/                 # shared logic, used by all Lambdas + local scripts
│   ├── config.py           # loads .env
│   ├── pdf_utils.py        # PDF -> text (pdfplumber, text-based PDFs only)
│   ├── bedrock_client.py   # extraction prompt (JSON, with retry) + message drafting
│   ├── dynamo.py           # DynamoDB read/write helpers
│   └── state_machine.py    # the "plans, acts, adapts over time" logic
├── lambdas/
│   ├── create_case/        # POST /cases
│   ├── get_case/           # GET /cases/{case_id}
│   ├── confirm_case/       # POST /cases/{case_id}/confirm
│   ├── timeline/           # GET /cases/{case_id}/timeline
│   ├── advance_time/       # POST /cases/{case_id}/advance-time  (DEMO ONLY)
│   └── daily_check/        # scheduled Lambda, triggered by EventBridge
├── scripts/
│   ├── setup_dynamodb.py   # one-time table creation
│   └── run_local_demo.py   # proves the whole flow works, no Lambda needed
├── tests/
│   └── sample_contract.txt # sample contract for testing extraction
├── test_bedrock.py         # run first - confirms Bedrock access works
├── build_lambda.sh / .ps1  # packages a Lambda folder into a deployable zip
├── requirements.txt
└── .env.example
```

## Local setup

This project is easiest to run locally with a Python 3.12 environment and real AWS credentials from the sandbox access portal. The AWS credentials are temporary and expire every ~12 hours, so you may need to refresh them during a session.

### 1) Create a Python environment

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Copy your environment variables

Copy `.env.example` to `.env` and fill in values from the AWS access portal.

macOS / Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Your `.env` should look like this:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-6-v1
DYNAMODB_TABLE=Cases
S3_BUCKET=contract-advocate-uploads
```

Important:

- These are TEMPORARY AWS sandbox credentials.
- They expire and need refreshing.
- Do not copy these into the Lambda environment variables in AWS.
- Lambda should use its IAM execution role instead.

### 3) Confirm Bedrock access

In the AWS Bedrock console, make sure:

- you are in `us-east-1`
- the model in `BEDROCK_MODEL_ID` is enabled in your account
- the model works in the Bedrock playground before trying the Lambda

### 4) Test Bedrock connectivity locally

```bash
python test_bedrock.py
```

You should see a one-sentence greeting printed. Do not continue until this works.

### 5) Create the DynamoDB table

```bash
python scripts/setup_dynamodb.py
```

### 6) Run the full local demo

```bash
python scripts/run_local_demo.py
```

This extracts the sample contract, creates a case, confirms it, then simulates time passing so you can see escalation messages get drafted.

## Building a Lambda package

Lambda runs on Linux, not Windows. If you package the zip on a native Windows machine, compiled libraries like `cryptography` can break inside the Lambda runtime.

The safest options are:

- Windows: use WSL
- macOS: use a Linux container or local Linux environment
- easiest cross-platform option: Docker

### Option A: WSL on Windows

Open WSL and run:

```bash
cd /mnt/c/Users/your-user/Desktop/contract-advocate/contract-advocate
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x build_lambda.sh
./build_lambda.sh create_case
```

This creates:

```text
build/create_case.zip
```

### Option B: Docker (recommended on macOS and Windows)

From the repo root, use the `linux/amd64` platform explicitly. This matters on
Apple Silicon Macs: Lambda must receive Linux binaries, not macOS or ARM
binaries.

macOS / Linux:

```bash
docker run --rm --platform linux/amd64 -v "$PWD":/app -w /app python:3.12 bash
```

Windows PowerShell:

```powershell
docker run --rm --platform linux/amd64 -v "${PWD}:/app" -w /app python:3.12 bash
```

Then inside the container:

```bash
rm -rf build/create_case build/create_case.zip
pip install -r requirements.txt
apt-get update && apt-get install -y zip
chmod +x build_lambda.sh
./build_lambda.sh create_case
```

This creates the zip in your local repo folder, so it appears as:

```text
build/create_case.zip
```

Important:

- do not upload the folder `build/create_case`
- upload the zip file directly
- use Docker or WSL when possible; the PowerShell builder also targets the
  Lambda Linux x86_64 wheels explicitly

Before uploading, verify the native dependency is a Linux ELF file:

```bash
unzip -p build/create_case.zip cryptography/hazmat/bindings/_rust.abi3.so > /tmp/_rust.abi3.so
file /tmp/_rust.abi3.so
```

The output must contain `ELF`. If it says `Mach-O`, the ZIP was built on macOS
outside Docker. If it says `PE32`, it was built on Windows.

## Deploying a Lambda in AWS

Each Lambda needs its dependencies + the shared `common/` code bundled with its handler. The build script does this for you.

### 1) Create the Lambda function

In AWS Lambda:

1. Click Create function
2. Choose Author from scratch
3. Runtime: Python 3.12
4. Function name: `create_case`
5. Create function

### 2) Upload the zip

On the Code tab:

- choose Upload from
- select `.zip file`
- upload `build/create_case.zip`

### 3) Set the handler

Set the handler to:

```text
handler.lambda_handler
```

### 4) Set the timeout

Set the timeout to at least 30 seconds for `create_case` because it does PDF extraction + model inference + DynamoDB writes.

### 5) Set environment variables

Under Configuration > Environment variables, set only the app values, not AWS secret keys.

```env
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-6-v1
DYNAMODB_TABLE=Cases
S3_BUCKET=contract-advocate-uploads
```

Do not add these keys to Lambda environment variables:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`

### 6) Create the execution role policy

This is the most important AWS step. The function needs an IAM role with permission to call Bedrock and DynamoDB.

In the Lambda console:

1. Open the function
2. Go to Configuration > Permissions
3. Click the execution role name
4. In IAM, click Add permissions > Create inline policy
5. Choose JSON
6. Paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    },
    {
      "Sid": "DynamoCaseTableAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan"
      ],
      "Resource": ["arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/Cases"]
    },
    {
      "Sid": "S3UploadAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::contract-advocate-uploads/*"]
    }
  ]
}
```

Replace:

- `YOUR_ACCOUNT_ID` with your AWS account ID
- `us-east-1` with your region if different
- `Cases` with your table name if changed

### 7) Test the function

For a smoke test, use a Function URL with auth type `NONE`.

Why: `AWS_IAM` requires signed AWS requests, which causes `403 Forbidden` from a browser or Postman unless you add SigV4 signing. For internal testing, `NONE` is the easiest choice.

#### Function URL setup

1. Configuration > Function URL
2. Create function URL
3. Auth type: `NONE`
4. Save

Then test with:

```json
{
  "user_id": "demo-user",
  "pdf_base64": "<base64 encoded PDF bytes>"
}
```

For local testing, use the same PDF file and base64 encode it with:

```bash
python -c "import base64; print(base64.b64encode(open('sample.pdf','rb').read()).decode())"
```

### 8) Repeat for every Lambda

Repeat the same deployment flow for:

- `create_case`
- `get_case`
- `confirm_case`
- `timeline`
- `advance_time`
- `daily_check`

For `daily_check`, do not use a Function URL. Trigger it with an EventBridge Scheduler rule instead.

## Team handoff checklist

For anyone new to AWS, these are the tasks to complete in order:

1. Copy `.env.example` to `.env` and fill in AWS sandbox credentials
2. Run `python test_bedrock.py` locally and confirm it works
3. Run `python scripts/setup_dynamodb.py`
4. Build the Lambda zip in Docker/WSL
5. Upload the zip to Lambda using Python 3.12 runtime
6. Set environment variables in the Lambda console
7. Create the execution role policy with Bedrock + DynamoDB permissions
8. Enable Function URL with auth type `NONE` for testing
9. Test with a real PDF payload
10. Repeat for the next Lambda

This is the exact flow we used to get the backend working and is simple enough for a teammate with no AWS background to follow step by step.

## API contract (for the frontend team)

**`POST /cases`**

```json
// request
{ "user_id": "demo-user", "pdf_base64": "<base64-encoded PDF bytes>" }
// response
{ "case_id": "abc123", "status": "EXTRACTED" }
```

**`GET /cases/{case_id}`** - full case object (status, clauses_flagged,
obligations, message_history).

**`POST /cases/{case_id}/confirm`**

```json
// request (obligations optional - only send if the user edited something)
{ "obligations": [ { "type": "payment_due", "date": "2026-09-10", ... } ] }
// response
{ "status": "AWAITING_PAYMENT" }
```

**`GET /cases/{case_id}/timeline`**

```json
{
  "case_id": "abc123",
  "events": [{ "date": "...", "type": "...", "detail_or_content": "..." }]
}
```

**`POST /cases/{case_id}/advance-time`** - demo/debug only, not a real feature

```json
// request
{ "days": 25 }
// response: the full updated case object
```

## Known limitations (be upfront about these in the demo/deck)

- **Scanned/image PDFs aren't supported** - only text-based PDFs. Handling
  scanned contracts would need OCR (e.g. AWS Textract), which we've
  deliberately left out to stay in scope for the week.
- **`advance-time` is a demo convenience**, not a real product feature -
  explain this clearly when demoing so it doesn't look like you're faking
  functionality.
- **No auth** - fine for a hackathon demo, would need to be added for
  anything real.
- **DynamoDB scan in `list_open_cases`** - fine at hackathon data volumes;
  would need a Global Secondary Index on `status` at real scale.
- Only **`payment_due`** obligations currently trigger the chase/escalate
  flow. Other obligation types (renewal, deliverable, termination) are
  extracted and shown on the timeline, but don't yet trigger their own
  reminder logic - that's a good "if we have time" extension.
