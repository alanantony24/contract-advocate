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

## Setup (do this once)

1. **Python env**
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Credentials** - copy `.env.example` to `.env` and fill in the three AWS
   values from the access portal (Access keys). These are temporary sandbox
   credentials and **expire every 12 hours** - you'll need to refresh them
   from the portal each session.

3. **Confirm region + model access** - in the Bedrock console, make sure
   you're in `us-east-1` and have access to the model ID in `.env`
   (`BEDROCK_MODEL_ID`). Test it in the Bedrock playground first if unsure.

4. **Test Bedrock connectivity:**
   ```
   python test_bedrock.py
   ```
   You should see a one-sentence greeting printed. Don't move on until this works.

5. **Create the DynamoDB table:**
   ```
   python scripts/setup_dynamodb.py
   ```
6. **Run the full local demo** (no Lambda deployment needed yet):
   ```
   python scripts/run_local_demo.py
   ```
   This extracts the sample contract, creates a case, confirms it, then
   simulates time passing so you can see escalation messages get drafted.
   If this works end to end, your core logic is solid.

## Deploying a Lambda

Each Lambda needs its dependencies + the shared `common/` code bundled with
its handler. The build scripts do this for you:

```
./build_lambda.sh create_case          # Mac/Linux
.\build_lambda.ps1 create_case         # Windows PowerShell
```

This produces `build/create_case.zip`. In the Lambda console:
1. Create a function (Python 3.12 runtime recommended - match whatever
   version you're developing locally).
2. Upload `build/create_case.zip` directly (drag and drop, or "Upload from" -
   .zip file).
3. Set the handler to `handler.lambda_handler`.
4. Attach an IAM role with permissions for `bedrock:InvokeModel`,
   `dynamodb:GetItem`/`PutItem`/`UpdateItem`/`Scan` on your table, and
   `s3:GetObject`/`PutObject` if you're using S3 for uploads.
5. Set environment variables on the function to match your `.env` (Lambda
   doesn't read your local `.env` file - you set these in the console under
   Configuration > Environment variables).
6. Enable a **Function URL** (Configuration > Function URL) so the frontend
   can call it directly - this avoids the added cost/complexity of API Gateway.

Repeat for each of the six lambdas: `create_case`, `get_case`,
`confirm_case`, `timeline`, `advance_time`, `daily_check`.

For `daily_check`, instead of a Function URL, set up an **EventBridge
Scheduler** rule (e.g. once a day) as its trigger - it's meant to run in the
background, not be called by the frontend.

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
{ "case_id": "abc123", "events": [ { "date": "...", "type": "...", "detail_or_content": "..." } ] }
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