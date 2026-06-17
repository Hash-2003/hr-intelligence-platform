# HR Intelligence Platform

HR Intelligence Platform is an LLM-powered backend system for HR request routing, memory-aware agent orchestration, audit logging, controlled HR document ingestion, traceable policy-grounded response generation, email-like webhook intake, and risk-based human review.

The project started as a technical challenge implementation and is now being extended into a more complete AI engineering platform.

## Features

- FastAPI backend
- LangGraph orchestration workflow
- LLM-based intent classification
- Intent correction guardrails for high-signal HR requests
- Specialist HR agents:
  - Scheduling Agent
  - Leave Agent
  - Compliance Agent
  - Clarification Agent
- Two-tier memory system:
  - Short-Term Memory, STM
  - Long-Term Memory, LTM
- Significance scoring for memory promotion
- Persistent HR request/case records
- Agent run persistence
- Controlled HR document ingestion from local policy files
- HR document chunk storage
- Keyword-based policy context retrieval
- Policy context injection into agent prompts
- Persisted policy source traceability for HR requests
- Email-like webhook intake for HR requests
- Timezone-aware datetime context using configurable `APP_TIMEZONE`
- Webhook `received_at` timestamp support for date-sensitive requests
- Deterministic leave date fact extraction for relative leave dates
- Leave notice deadline validation before LLM response generation
- Human-reviewable draft response workflow
- Risk-based Human-in-the-Loop review metadata
- Rule-based and optional LLM-assisted review decision layer
- Draft approval and rejection workflow
- Isolated test database configuration
- Pagination metadata for main operational list endpoints
- Generic audit event metadata for system lifecycle events
- Audit event filtering for operational traceability
- Draft queue filtering for HR review workflows
- Draft send simulation after approval
- Email-formatted draft responses using a dedicated formatter
- Email event retrieval and filtering endpoints
- Reviewer/admin actor metadata in draft lifecycle audit events
- Mock header-based RBAC for reviewer/admin operations
- Explicit draft state transition validation with `409 Conflict` responses for invalid lifecycle actions
- Centralized domain constants for draft statuses, review actions, priorities, email event statuses, audit events, resource types, and roles
- Deterministic PII redaction service for sensitive prompt preparation
- LLM user prompts redacted before provider calls
- PII redaction counts tracked on LLM calls
- Specialist agent PII redaction metadata persisted in agent run records
- Append-only audit logging
- Safe failure handling without exposing raw Python stack traces
- SQLite database
- Environment-based configuration using `.env`
- Automated API tests
- Postman collection for API testing

## Planned Improvements

- Source-aware response formatting
- Embedding-based semantic retrieval
- Safety Agent for crisis-sensitive or non-HR emergency messages
- Retry/failure tracking for webhook processing
- Persist richer LLM-call observability beyond specialist agent runs
- Add optional redacted prompt snapshots only if a clear audit/security need exists
- Real email integration through n8n, Gmail, Microsoft Graph, or a mail parser
- Docker support
- PostgreSQL and migration support
- CI workflow
- Real JWT/OAuth authentication and production-grade role-based access control

## Tech Stack

- Python 3.11+
- FastAPI
- LangGraph
- SQLite
- SQLAlchemy
- Pydantic
- OpenAI-compatible LLM API
- Pytest
- Postman

## System Architecture

The request pipeline follows this flow:

```text
POST /requests or POST /webhooks/email
    ↓
Create HR request record
    ↓
Load STM and LTM memory
    ↓
Load timezone-aware datetime context
    ↓
Classify intent
    ↓
Retrieve relevant HR policy chunks
    ↓
Resolve deterministic leave date facts, if leave intent
    ↓
Route using LangGraph conditional edges
    ↓
Redact sensitive user prompt content before LLM provider calls
    ↓
Specialist agent execution
    ↓
Save agent run record
    ↓
Persist PII redaction metadata for specialist agent run
    ↓
Persist policy sources used
    ↓
Update HR request status and result
    ↓
Apply risk-based review decision logic
    ↓
Create formatted reviewable email draft, for webhook requests
    ↓
Human review: edit, approve, reject, or send simulation
    ↓
Write generic audit events for draft lifecycle actions
    ↓
Save short-term memory
    ↓
Promote significant context to long-term memory
    ↓
Write append-only audit log
    ↓
Return structured response
```

Supported intents:

```text
scheduling
leave
compliance
clarification
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Basic API information |
| GET | `/health` | Service health and LLM configuration status |
| POST | `/requests` | Handle natural language HR request |
| POST | `/memory` | Manually add STM or LTM memory |
| GET | `/memory/{user_id}` | Retrieve user memory |
| GET | `/audit` | Retrieve audit logs |
| GET | `/documents` | Retrieve ingested HR document metadata |
| GET | `/documents/{document_id}` | Retrieve a specific HR document |
| GET | `/documents/{document_id}/chunks` | Retrieve chunks for a specific HR document |
| GET | `/hr-requests` | Retrieve persisted HR request records |
| GET | `/hr-requests/{request_id}` | Retrieve a specific HR request |
| GET | `/hr-requests/{request_id}/agent-runs` | Retrieve agent execution records for a request |
| GET | `/hr-requests/{request_id}/policy-sources` | Retrieve policy document chunks used by a request |
| POST | `/webhooks/email` | Process an incoming email-like HR request webhook |
| GET | `/email-events` | Retrieve stored email/webhook events with filters and pagination metadata |
| GET | `/email-events/{event_id}` | Retrieve a specific stored email/webhook event |
| GET | `/drafts` | Retrieve generated draft responses |
| GET | `/drafts/{draft_id}` | Retrieve a specific draft response |
| PATCH | `/drafts/{draft_id}` | Update the body of an editable draft response |
| POST | `/drafts/{draft_id}/approve` | Mark a draft response as approved |
| POST | `/drafts/{draft_id}/reject` | Mark a draft response as rejected |
| POST | `/drafts/{draft_id}/send` | Simulate sending an approved draft response |


## Paginated Operational List Responses

Main operational list endpoints return pagination metadata using a consistent response shape.

Paginated endpoints currently include:

```text
GET /drafts
GET /audit
GET /email-events
GET /hr-requests
```

Response shape:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Common query parameters:

```http
GET /drafts?limit=20&offset=0
GET /audit?event_type=draft_sent&limit=20&offset=0
GET /email-events?status=processed&limit=20&offset=0
GET /hr-requests?intent=leave&limit=20&offset=0
```


## Mock Authentication and RBAC

The current implementation includes a lightweight mock authentication and authorization layer for reviewer/admin operations.

Protected review and observability endpoints require request headers:

```http
X-User-Id: hr_reviewer_001
X-User-Role: hr_reviewer
```

Supported mock roles:

```text
employee
hr_reviewer
admin
```

Current access rules:

| Role | Access |
|---|---|
| `employee` | Can submit normal HR requests and webhook-style intake remains public for testing/integration. Cannot access review queues or audit/event views. |
| `hr_reviewer` | Can view, edit, approve, reject, and send-simulate drafts. Can view audit logs and email events. |
| `admin` | Has the same reviewer access in the current mock RBAC layer and is reserved for broader admin operations later. |

Protected endpoints currently include:

```text
GET /drafts
GET /drafts/{draft_id}
PATCH /drafts/{draft_id}
POST /drafts/{draft_id}/approve
POST /drafts/{draft_id}/reject
POST /drafts/{draft_id}/send
GET /audit
GET /email-events
GET /email-events/{event_id}
```

Missing authentication headers return `401 Unauthorized`. Valid users with insufficient role permissions return `403 Forbidden`.

This is intentionally a mock RBAC layer for local development and portfolio demonstration. A production version should replace it with JWT/OAuth or enterprise identity integration.

## Date-Aware Leave Handling

The system includes deterministic leave date fact extraction for leave-related requests.

The LLM is not responsible for calculating leave dates, notice deadlines, or notice status. Instead, the backend resolves supported relative date phrases in code and passes structured facts to the Leave Agent.

Currently supported examples include:

```text
next Monday
tomorrow
today
a week after next Monday
one week after next Monday
for 2 days
```

For example, if an email is received on `2026-05-17` and the user asks for annual leave for 2 days starting from a week after next Monday, the backend resolves:

```text
requested start date: 2026-05-25 Monday
requested end date: 2026-05-26 Tuesday
duration: 2 days
latest standard submission date: 2026-05-18 Monday
notice status: not_missed
```

The Leave Agent then uses these resolved facts to generate a human-friendly response without performing calendar arithmetic itself.

## Draft Response Workflow

The system supports a human-reviewable draft response workflow for email-like HR requests.

When an incoming email webhook is processed, the system:

```text
Receives email-like webhook payload
    ↓
Stores the email event
    ↓
Creates an HR request
    ↓
Runs the LangGraph agent workflow
    ↓
Generates an AI-assisted response
    ↓
Applies review decision logic
    ↓
Formats the agent response as an email-style draft
    ↓
Stores the response as a draft
```

The generated response is not treated as a sent email. It is stored as a draft for review.

Each draft stores:

```text
draft_id
request_id
email_event_id
recipient_email
subject
body
status
review_action
review_required
review_priority
review_reason
review_decision_source
```

Draft lifecycle:

```text
draft → approved → sent
draft → rejected
```

The `sent` state is currently a simulation. It marks an approved draft as sent and records the action in the audit log, but it does not send a real email.


Invalid lifecycle transitions are rejected with `409 Conflict`. For example, a draft cannot be sent before approval, and an approved, rejected, or sent draft cannot be edited as a normal draft.

State rules:

```text
draft → approved → sent
draft → rejected
```

Invalid examples:

```text
draft → sent
approved → rejected
rejected → approved
sent → update
```

Reviewer/admin actions performed through protected endpoints include actor metadata in draft lifecycle audit events:

```json
{
  "actor_user_id": "hr_reviewer_test",
  "actor_role": "hr_reviewer"
}
```

Webhook-generated drafts are formatted as email replies:

```text
Agent response
    ↓
EmailDraftFormatter
    ↓
Reviewable email draft body
```


## Risk-Based Human-in-the-Loop Review

The platform uses a risk-based Human-in-the-Loop design instead of sending every AI-generated response to mandatory human review.

A `ReviewDecisionService` evaluates each processed HR request and assigns review metadata.

Possible review actions:

```text
auto_response
review_optional
review_required
escalated
```

Review priorities:

```text
low
medium
high
critical
```

The current review decision layer uses deterministic rules first. It can optionally use an LLM-assisted classifier for ambiguous soft-risk cases, but deterministic high-risk rules remain the final authority.

Examples:

| Request Type | Review Action | Reason |
|---|---|---|
| Simple policy question | `auto_response` | Low-risk policy FAQ |
| Normal leave request | `review_optional` | Action-oriented HR request |
| Harassment/discrimination complaint | `review_required` | Sensitive workplace misconduct concern |
| Salary/payroll dispute | `review_required` | Sensitive HR topic |
| Legal/security concern | `review_required` | Legal, compliance, or data-protection risk |
| Safety-sensitive message | `escalated` | Critical safety concern |

This reduces unnecessary human workload while still routing sensitive or uncertain cases to human review.

## Setup Instructions

### 1. Clone the Repository

```powershell
git clone https://github.com/Hash-2003/hr-intelligence-platform
cd hr-intelligence-platform
```

### 2. Create and Activate Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create `.env`

Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

Then add your LLM API key.

Example:

```env
APP_NAME=HR Intelligence Platform
APP_TIMEZONE=Asia/Colombo
APP_ENV=development
DATABASE_URL=sqlite:///./hr_intelligence_platform.db

LLM_PROVIDER=groq
LLM_API_KEY=your_api_key_here
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2

INTENT_CONFIDENCE_THRESHOLD=0.65
STM_LIMIT_PER_USER=10
LTM_SIGNIFICANCE_THRESHOLD=0.75
```

## Model Configuration

The application uses an OpenAI-compatible LLM client. The model can be changed through `.env`.

Recommended Groq model for the current implementation:

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
```

A deterministic backend service handles leave-date calculation, so the LLM is mainly used for intent classification, policy-grounded explanation, and response generation.

## PII Redaction Before LLM Calls

The platform includes a deterministic PII redaction layer at the centralized `LLMService` boundary.

Current behavior:

```text
Raw request/email text may be stored internally for HR traceability
    ↓
User prompt text is redacted before being sent to the LLM provider
    ↓
The LLM receives sanitized prompt content
    ↓
Redaction counts are tracked for debugging and auditability
    ↓
Specialist agent run records persist redaction metadata
```

Currently redacted patterns include:

```text
email addresses → [EMAIL]
phone numbers → [PHONE]
URLs → [URL]
Sri Lankan NIC-like national IDs → [NATIONAL_ID]
employee IDs / employee numbers → [EMPLOYEE_ID]
salary/payroll amounts → [SALARY]
```

The system does not store the full redacted prompt as an audit artifact yet. Instead, it stores safe metadata on specialist agent runs using `pii_redaction_counts`.

Example stored metadata:

```json
{
  "EMAIL": 1,
  "PHONE": 1,
  "URL": 0,
  "NATIONAL_ID": 0,
  "EMPLOYEE_ID": 0,
  "SALARY": 0
}
```

This provides privacy observability without duplicating sensitive prompt content in logs.

Current scope note:

```text
PII redaction currently protects centralized LLM user-prompt calls.
The original HR request or email event can still be stored in the backend for HR reviewer traceability.
```

Future improvements may include name detection, address detection, consistent pseudonymization, encrypted raw-message storage, and a dedicated `llm_call_logs` table for classifier-level and agent-level observability.

## Run the Application

```powershell
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

The SQLite database file is not committed to Git. It is created automatically when the application starts.

## Ingest HR Policy Documents

Controlled HR documents are stored in:

```text
data/hr_documents/
```

Current sample documents include:

```text
leave_policy.md
overtime_policy.md
code_of_conduct.md
```

Run the ingestion script before testing document-grounded responses:

```powershell
python -m scripts.ingest_documents
```

The ingestion process reads the local policy files, creates document records, splits the text into chunks, stores the chunks in SQLite, and skips unchanged documents using content hashing.

## Example Requests

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "service": "HR Intelligence Platform",
  "environment": "development",
  "llm_provider": "groq",
  "llm_configured": true
}
```

### Handle HR Request

```http
POST /requests
```

Body:

```json
{
  "user_id": "user_001",
  "message": "I want to apply for annual leave next Monday."
}
```

Example response:

```json
{
  "request_id": "generated-uuid",
  "intent": "leave",
  "confidence": 1.0,
  "agent": "leave_agent",
  "response": "Generated HR response...",
  "memory_used": true
}
```

### Process Email-Like Webhook

```http
POST /webhooks/email
```

Body:

```json
{
  "sender_email": "employee@example.com",
  "sender_name": "Kasun Perera",
  "subject": "Annual leave request",
  "body": "I would like to apply for annual leave for 2 days starting from a week after next Monday.",
  "received_at": "2026-05-17T10:30:00"
}
```

Example response:

```json
{
  "event_id": "generated-event-id",
  "request_id": "generated-request-id",
  "draft_id": "generated-draft-id",
  "intent": "leave",
  "agent": "leave_agent",
  "response": "Generated HR response...",
  "status": "processed",
  "review_action": "review_optional",
  "review_required": false,
  "review_priority": "medium",
  "review_reason": "Leave request detected; draft may be reviewed before action.",
  "review_decision_source": "deterministic"
}
```


## Email Event Retrieval

Incoming email-like webhook events are persisted and can be inspected through API endpoints.

### Retrieve Email Events

```http
GET /email-events
```

Optional filters:

```http
GET /email-events?status=processed
GET /email-events?sender_email=employee@example.com
GET /email-events?source=webhook
GET /email-events?linked_request_id={request_id}
GET /email-events?limit=20&offset=0
```

### Retrieve One Email Event

```http
GET /email-events/{event_id}
```

This improves traceability from the original email/webhook event to the generated HR request and draft response.

### Policy-Grounded Request Example

```http
POST /requests
```

Body:

```json
{
  "user_id": "user_001",
  "message": "Can I work overtime first and get approval later?"
}
```

Expected behavior:

```text
The request should route to the Compliance Agent and use the Overtime Policy context.
The answer should state that overtime requires prior approval before the hours are worked.
```

### Add Long-Term Memory

```http
POST /memory
```

Body:

```json
{
  "user_id": "user_001",
  "content": "User prefers morning interviews.",
  "memory_type": "ltm",
  "significance": 0.9
}
```

### Retrieve Memory

```http
GET /memory/user_001
```

### Retrieve Audit Logs

```http
GET /audit
```

Optional filters:

```http
GET /audit?user_id=user_001
GET /audit?event_type=draft_sent
GET /audit?resource_type=draft_response
GET /audit?resource_id={draft_id}
GET /audit?request_id={request_id}
GET /audit?status=success
GET /audit?limit=20&offset=0
```

## HR Request Retrieval

### Retrieve HR Requests

```http
GET /hr-requests
```

Optional filters:

```http
GET /hr-requests?user_id=user_001
GET /hr-requests?status=success
GET /hr-requests?intent=leave
GET /hr-requests?source_type=email_webhook
GET /hr-requests?limit=20&offset=0
```

This returns paginated persisted HR request/case records created through the request pipeline.

### Retrieve One HR Request

```http
GET /hr-requests/{request_id}
```

This returns the stored classification, selected agent, response, status, and timestamps for one request.

### Retrieve Agent Runs

```http
GET /hr-requests/{request_id}/agent-runs
```

This returns specialist agent execution records linked to the HR request.

Agent run responses include optional PII redaction metadata when available:

```json
{
  "agent_name": "leave_agent",
  "status": "success",
  "pii_redaction_counts": "{\"EMAIL\": 1, \"PHONE\": 0, \"URL\": 0, \"NATIONAL_ID\": 0, \"EMPLOYEE_ID\": 0, \"SALARY\": 0}"
}
```

This metadata records redaction counts only. It does not expose the raw sensitive values or the full prompt sent to the model.


### Retrieve Policy Sources Used by a Request

```http
GET /hr-requests/{request_id}/policy-sources
```

This returns the HR policy document chunks that were retrieved and injected into the agent prompt for a specific request.

Example response:

```json
[
  {
    "id": 1,
    "request_id": "generated-request-id",
    "document_id": 2,
    "document_title": "Overtime Policy",
    "filename": "overtime_policy.md",
    "chunk_id": 4,
    "chunk_index": 0,
    "score": 7,
    "created_at": "2026-05-20T10:00:00"
  }
]
```

This endpoint improves traceability by showing which policy sources influenced an agent response.

## Draft Response Retrieval and Review

Protected draft endpoints require mock reviewer/admin headers:

```http
X-User-Id: hr_reviewer_test
X-User-Role: hr_reviewer
```


### Retrieve Drafts

```http
GET /drafts
```

Optional filters:

```http
GET /drafts?status=draft
GET /drafts?status=approved
GET /drafts?status=sent
GET /drafts?review_required=true
GET /drafts?review_priority=high
GET /drafts?review_action=review_required
GET /drafts?recipient_email=employee@example.com
GET /drafts?limit=20&offset=0
```

### Retrieve One Draft

```http
GET /drafts/{draft_id}
```

### Update Draft Body

```http
PATCH /drafts/{draft_id}
```

Body:

```json
{
  "body": "Updated draft response text."
}
```

Only drafts with `status = draft` are editable.

### Approve Draft

```http
POST /drafts/{draft_id}/approve
```

This changes the draft status to:

```text
approved
```

### Reject Draft

```http
POST /drafts/{draft_id}/reject
```

This changes the draft status to:

```text
rejected
```

### Send Approved Draft Simulation

```http
POST /drafts/{draft_id}/send
```

Only drafts with `status = approved` can be marked as sent.

This changes the draft status to:

```text
sent
```

This is a send simulation only. The system does not send a real email yet.

## Document Retrieval

### Retrieve Documents

```http
GET /documents
```

### Retrieve One Document

```http
GET /documents/{document_id}
```

### Retrieve Document Chunks

```http
GET /documents/{document_id}/chunks
```

These endpoints expose the controlled HR policy documents and chunks available for policy-grounded retrieval.

## Traceable Policy Context Retrieval

The system includes a first-pass document-grounded retrieval pipeline for HR policy context.

The retrieval flow is:

```text
User request
    ↓
Intent classification
    ↓
Keyword-based policy chunk retrieval
    ↓
Policy context injected into agent prompt
    ↓
Agent response generated
    ↓
Policy source metadata persisted
```

Current retrieval uses transparent keyword-based scoring rather than embeddings. This keeps the first version easy to inspect and debug. Retrieved policy chunks are injected into the relevant agent prompt before response generation.

For each HR request, the retrieved policy sources are persisted and can be inspected using:

```http
GET /hr-requests/{request_id}/policy-sources
```

This makes the RAG pipeline traceable because the system records which document chunks were used for each generated response.

## Memory Design

The system uses two memory layers.

### Short-Term Memory

Short-term memory stores recent user interactions. It is useful for immediate conversational context.

Current rules:

- Stored for recent interactions
- Has expiry metadata
- Limited by `STM_LIMIT_PER_USER`

### Long-Term Memory

Long-term memory stores significant user preferences or useful HR context.

A deterministic significance score is calculated using transparent rules:

- User preferences increase the score
- Time/date references increase the score
- HR-related terms increase the score
- Supported HR intents increase the score

If the score is above `LTM_SIGNIFICANCE_THRESHOLD`, the item is promoted to long-term memory.

## Audit Log Design

The audit log is append-only.

Each request-level audit record includes:

- request ID
- user ID
- original message
- classified intent
- confidence score
- selected agent
- response summary
- status
- error message, if any
- timestamp

The audit layer also supports generic audit event metadata:

- `event_type`
- `resource_type`
- `resource_id`
- `details_json`

Examples of generic audit events include:

```text
request_processed
draft_created
draft_updated
draft_approved
draft_rejected
draft_sent
```

Draft lifecycle audit events may also include reviewer/admin actor metadata inside `details_json`:

```json
{
  "actor_user_id": "hr_reviewer_test",
  "actor_role": "hr_reviewer"
}
```

PII redaction metadata is stored on specialist agent run records, not as raw prompt text in audit details.

The API does not provide update or delete operations for audit logs.

## Failure Handling

The system avoids exposing raw internal stack traces to users.

Invalid draft lifecycle actions return `409 Conflict` with structured state-transition details, while missing draft IDs still return `404 Not Found`.

If the LLM provider fails during specialist agent execution, the workflow returns a polite fallback response and records the failure in the audit log.

If the LLM intent classifier returns an obvious mismatch for high-signal HR requests, a deterministic correction layer adjusts the intent. For example, explicit annual leave requests are corrected to the `leave` intent.

## Running Tests

```powershell
pytest
```

The `/requests` endpoint test uses a mocked workflow to avoid external LLM API calls during automated testing.

## Postman Collection

A Postman collection is included at:

```text
docs/postman_collection.json
```

To use it:

1. Start the FastAPI server.
2. Open Postman.
3. Import `docs/postman_collection.json`.
4. Run the included requests against `http://127.0.0.1:8000`.

The collection includes requests for health checks, HR request handling, memory management, HR request retrieval, document retrieval, and audit retrieval.

## Known Limitations

- The current policy retrieval method is keyword-based rather than embedding-based.
- Source metadata is persisted, but responses do not yet include source citations in the text.
- No real HRIS, calendar, leave-management, payroll, legal, or email-sending system is integrated.
- Draft sending is currently simulated; no real email is sent yet.
- The system uses controlled local policy documents rather than an admin document management interface.
- LLM responses depend on the configured provider and model.
- The current memory retrieval strategy is simple and deterministic.
- SQLite is suitable for local development, not high-concurrency production deployment.
- Authentication/RBAC is currently header-based mock auth, not production JWT/OAuth.
- Crisis-sensitive or non-HR emergency messages are not yet handled by a dedicated Safety Agent.
- PII redaction is deterministic and pattern-based; it does not yet detect all names, addresses, or free-form sensitive details.
- Redaction metadata is currently persisted for specialist agent runs, not every classifier or auxiliary LLM call.
- Operational list endpoints are paginated, but deeper pagination metadata may still be expanded later.

## Project Status

Core backend functionality, controlled document ingestion, traceable policy context retrieval, request persistence, memory, audit logging, email-like webhook intake, deterministic leave date handling, email-formatted draft responses, draft approval/rejection/send simulation, explicit draft state transition validation, mock RBAC for review operations, reviewer actor metadata in audit events, deterministic PII redaction before LLM calls, persisted PII redaction metadata for specialist agent runs, risk-based review metadata, filterable operational queues, pagination metadata, and automated tests are implemented.
