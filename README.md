# HR Intelligence Platform

LLM-powered multi-agent task routing and memory engine for an HR automation platform.

This project was developed as a technical challenge for an AI Engineer Intern application. It uses a central LangGraph-based orchestrator to classify natural language HR requests, route them to specialist agents, inject memory context, and maintain an append-only audit trail.

## Features

- FastAPI backend
- LangGraph orchestration workflow
- LLM-based intent classification
- Specialist HR agents:
  - Scheduling Agent
  - Leave Agent
  - Compliance Agent
  - Clarification Agent
- Two-tier memory system:
  - Short-Term Memory, STM
  - Long-Term Memory, LTM
- Significance scoring for memory promotion
- Append-only audit logging
- Safe failure handling without exposing raw Python stack traces
- SQLite database
- Environment-based configuration using `.env`
- Automated API tests

## Planned improvements:

- HR policy document ingestion
- Document-grounded RAG for compliance and leave questions
- Email/webhook-triggered HR request intake
- Improved database schema for HR cases and agent runs
- Draft email response generation
- Human review workflow
- Docker support
- PostgreSQL and migration support

## Tech Stack

- Python 3.11+
- FastAPI
- LangGraph
- SQLite
- SQLAlchemy
- Pydantic
- OpenAI-compatible LLM API
- Pytest

## System Architecture

The request pipeline follows this flow:

```text
POST /requests
    ↓
Load STM and LTM memory
    ↓
LLM intent classification
    ↓
Route using LangGraph conditional edges
    ↓
Specialist agent execution
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

## Setup Instructions

### 1. Clone the repository

```powershell
git clone https://github.com/Hash-2003/HR-Agent-Engine
cd hr-agent-engine
```

### 2. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

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
APP_NAME=HR Agent Engine
APP_ENV=development
DATABASE_URL=sqlite:///./hr_agent_engine.db

LLM_PROVIDER=groq
LLM_API_KEY=your_api_key_here
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=2

INTENT_CONFIDENCE_THRESHOLD=0.65
STM_LIMIT_PER_USER=10
LTM_SIGNIFICANCE_THRESHOLD=0.75
```

The system uses an OpenAI-compatible API client, so providers such as Groq can be used by setting the correct `LLM_BASE_URL`.

## Run the Application

```powershell
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

The SQLite database file is not committed to Git. It is created automatically when the application starts.

## Example Requests

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "service": "HR Agent Engine",
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

## Known Limitations

- Specialist agents use mock HR policies only.
- No real HRIS, calendar, leave-management, or legal system is integrated.
- LLM responses depend on the configured provider and model.
- The current memory retrieval strategy is simple and deterministic.
- SQLite is suitable for local assessment, not high-concurrency production deployment.

## Project Status

Core backend functionality is implemented and tested.