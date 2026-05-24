# HR Intelligence Platform

HR Intelligence Platform is an LLM-powered backend system for HR request routing, memory-aware agent orchestration, audit logging, controlled HR document ingestion, and traceable policy-grounded response generation.

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
- Append-only audit logging
- Safe failure handling without exposing raw Python stack traces
- SQLite database
- Environment-based configuration using `.env`
- Automated API tests
- Postman collection for API testing
- Email-like webhook intake for HR requests
- Timezone-aware datetime context using configurable `APP_TIMEZONE`
- Webhook `received_at` timestamp support for date-sensitive requests
- Deterministic leave date fact extraction for relative leave dates
- Leave notice deadline validation before LLM response generation

## Planned Improvements

- Email/webhook-triggered HR request intake
- Draft email response generation
- Human review workflow
- Source-aware response formatting
- Embedding-based semantic retrieval
- Safety Agent for crisis-sensitive or non-HR emergency messages
- Docker support
- PostgreSQL and migration support
- CI workflow

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
Specialist agent execution
    ↓
Save agent run record
    ↓
Persist policy sources used
    ↓
Update HR request status and result
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
For example, if an email is received on 2026-05-17 and the user asks for annual leave for 2 days starting from a week after next Monday, the backend resolves:
```text
requested start date: 2026-05-25 Monday
requested end date: 2026-05-26 Tuesday
duration: 2 days
latest standard submission date: 2026-05-18 Monday
notice status: not_missed
```
The Leave Agent then uses these resolved facts to generate a human-friendly response without performing calendar arithmetic itself.


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

Optional filter:

```http
GET /audit?user_id=user_001
```

## HR Request Retrieval

### Retrieve HR Requests

```http
GET /hr-requests
```

Optional user filter:

```http
GET /hr-requests?user_id=user_001
```

This returns persisted HR request/case records created through the request pipeline.

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

Each request records:

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

The API does not provide update or delete operations for audit logs.

## Failure Handling

The system avoids exposing raw internal stack traces to users.

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
- No real HRIS, calendar, leave-management, payroll, or legal system is integrated.
- The system uses controlled local policy documents rather than an admin document management interface.
- LLM responses depend on the configured provider and model.
- The current memory retrieval strategy is simple and deterministic.
- SQLite is suitable for local development, not high-concurrency production deployment.
- There is no authentication or role-based access control yet.
- Crisis-sensitive or non-HR emergency messages are not yet handled by a dedicated Safety Agent.

## Project Status

Core backend functionality, controlled document ingestion, traceable policy context retrieval, request persistence, memory, audit logging, and automated tests are implemented.
