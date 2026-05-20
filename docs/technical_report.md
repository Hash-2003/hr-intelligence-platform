# Technical Report: HR Intelligence Platform

## 1. Project Overview

This project implements an LLM-powered multi-agent task routing and memory engine for an HR automation platform. The system accepts natural language HR-related requests, classifies the intent using an LLM, routes the request to the most appropriate specialist agent through a LangGraph workflow, injects historical memory context, generates a response, and records the full processing path in an append-only audit log.

The main goal of the system is to demonstrate a clean backend architecture for agent orchestration, memory management, and auditability using FastAPI, LangGraph, SQLite, and an OpenAI-compatible LLM API.

The system supports four primary intent categories:

```text
scheduling
leave
compliance
clarification
```

The specialist agents are:

```text
Scheduling Agent
Leave Agent
Compliance Agent
Clarification Agent
```

The system is designed as an API-first backend. It does not include a frontend because the assignment requirements focus on REST API endpoints, orchestration, memory, and audit logging.

---

## 2. Technology Stack

The implementation uses the following technologies:

| Component | Technology |
|---|---|
| Backend framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM integration | OpenAI-compatible API client |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data validation | Pydantic |
| Configuration | `.env` using pydantic-settings |
| Testing | Pytest and FastAPI TestClient |

SQLite was selected because the challenge specifically requested SQLite integration and because it is simple for local evaluation. The database is created automatically on application startup.

---

## 3. High-Level Architecture

The system follows a modular architecture with separation of concerns.

```text
Client / Swagger / Postman
        ↓
FastAPI Routes
        ↓
LangGraph HRWorkflow
        ↓
Memory Loading
        ↓
LLM Intent Classification
        ↓
Conditional Agent Routing
        ↓
Specialist Agent Response
        ↓
Memory Update
        ↓
Audit Logging
        ↓
Structured API Response
```

The main modules are:

```text
app/api
```

Contains FastAPI route definitions.

```text
app/agents
```

Contains specialist HR agents.

```text
app/graph
```

Contains the LangGraph workflow.

```text
app/services
```

Contains reusable service logic for LLM calls, memory, audit logging, and intent classification.

```text
app/schemas
```

Contains Pydantic request and response models.

```text
app/database.py
```

Contains SQLAlchemy models, database engine setup, and session dependency.

---

## 4. REST API Endpoints

The system exposes the following endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Basic API information |
| `GET` | `/health` | Health monitoring and LLM configuration status |
| `POST` | `/requests` | Main natural language request handling endpoint |
| `POST` | `/memory` | Manual memory insertion for testing |
| `GET` | `/memory/{user_id}` | Retrieve short-term and long-term memory |
| `GET` | `/audit` | Retrieve audit logs |

Although the assignment mentions five core endpoint types, the implementation includes six actual endpoints because the root endpoint is also provided for convenience.

---

## 5. Request Handling Flow

The main request flow starts at:

```http
POST /requests
```

Example input:

```json
{
  "user_id": "user_001",
  "message": "I want to apply for annual leave next Monday."
}
```

The request is processed through the following steps:

1. A unique request ID is generated.
2. Short-term and long-term memory are loaded for the user.
3. The LLM classifies the user intent.
4. LangGraph routes the request to the appropriate specialist agent.
5. The selected agent generates a response using the user message and memory context.
6. The message is stored in short-term memory.
7. If the message has high significance, it is promoted to long-term memory.
8. An append-only audit log entry is created.
9. The final structured response is returned.

Example response:

```json
{
  "request_id": "generated-uuid",
  "intent": "leave",
  "confidence": 1.0,
  "agent": "leave_agent",
  "response": "Generated leave-related response...",
  "memory_used": true
}
```

---

## 6. LangGraph Workflow Design

LangGraph is used to model the agent system as a state graph.

The workflow state carries shared information between nodes, including:

```text
request_id
user_id
message
memory_context
memory_used
intent
confidence
reasoning_summary
selected_agent
response
status
error_message
```

The workflow structure is:

```text
load_memory
    ↓
classify_intent
    ↓
conditional routing
    ↓
scheduling_agent / leave_agent / compliance_agent / clarification_agent
    ↓
save_memory
    ↓
write_audit
    ↓
END
```

The conditional routing step uses the classified intent to decide which specialist agent receives the request.

Routing logic:

```text
scheduling     → Scheduling Agent
leave          → Leave Agent
compliance     → Compliance Agent
clarification  → Clarification Agent
```

If the intent is unsupported or uncertain, the workflow routes to the Clarification Agent.

This graph-based design keeps the orchestration explicit, testable, and easier to extend.

---

## 7. LLM Usage

The LLM is used in two main areas.

### 7.1 Intent Classification

The intent classifier asks the LLM to return structured JSON with:

```json
{
  "intent": "leave",
  "confidence": 0.95,
  "reasoning_summary": "The user is asking for annual leave."
}
```

Allowed intents are:

```text
scheduling
leave
compliance
clarification
```

The classification result is validated using Pydantic. If the LLM returns an invalid intent, invalid JSON, or a confidence score below the configured threshold, the system safely routes the request to the Clarification Agent.

### 7.2 Specialist Agent Responses

Each specialist agent uses the LLM to generate a domain-specific response.

The agents are prompted with:

```text
- agent role
- responsibilities
- relevant mock HR policy
- memory context
- user message
```

This keeps each agent focused on its own boundary.

---

## 8. Agent Design

### 8.1 Scheduling Agent

The Scheduling Agent handles:

```text
meetings
interviews
calendar coordination
rescheduling
appointment-related requests
```

It asks for missing scheduling details such as date, time, attendees, and meeting purpose. It does not claim that a real calendar event has been created.

### 8.2 Leave Agent

The Leave Agent handles:

```text
annual leave
sick leave
casual leave
vacation
absence
leave balance questions
```

It uses mock leave policy data and asks for missing details such as leave type, start date, end date, and reason.

### 8.3 Compliance Agent

The Compliance Agent handles:

```text
HR policy
workplace rules
overtime
salary changes
contracts
complaints
compliance-related questions
```

It uses mock compliance policy and avoids presenting itself as a legal authority. For final decisions, it recommends HR or legal review.

### 8.4 Clarification Agent

The Clarification Agent handles:

```text
unclear requests
low-confidence classification
unsupported requests
missing critical details
```

It asks targeted follow-up questions rather than guessing the user’s intent.

---

## 9. Memory System

The system implements a two-tier memory model.

### 9.1 Short-Term Memory

Short-term memory stores recent user interactions.

Purpose:

```text
- preserve immediate conversation context
- support follow-up requests
- keep recent HR discussion history
```

Current behavior:

```text
- records recent user messages
- includes expiry metadata
- limited by STM_LIMIT_PER_USER
```

### 9.2 Long-Term Memory

Long-term memory stores significant user preferences or important HR-related context.

Purpose:

```text
- preserve useful user preferences
- inject persistent context into future prompts
- support more personalized agent responses
```

Example:

```text
User prefers morning interviews.
```

### 9.3 Memory Context Injection

Before classification and agent execution, the memory service builds a text context block:

```text
Short-term memory:
- User asked about annual leave.

Long-term memory:
- User prefers morning interviews. (significance=0.90)
```

This memory context is injected into LLM prompts.

---

## 10. Significance Scoring Logic

The system uses a deterministic significance scoring method for deciding whether a message should be promoted to long-term memory.

This was chosen because it is transparent, easy to explain, and suitable for assessment.

The scoring considers:

```text
preference markers
time markers
HR-related markers
classified intent
```

Examples of preference markers:

```text
prefer
usually
always
remember
important
my manager
my team
my department
```

Examples of time markers:

```text
today
tomorrow
next week
morning
evening
weekdays
```

Examples of HR markers:

```text
leave
sick
annual
meeting
interview
salary
policy
contract
overtime
```

If the final score is greater than or equal to the configured `LTM_SIGNIFICANCE_THRESHOLD`, the memory is promoted to long-term memory.

This rule-based method is not as sophisticated as embedding-based retrieval, but it is predictable and easy to audit.

---

## 11. Audit Log Design

The audit log is append-only.

Each request records:

```text
request_id
user_id
original message
classified intent
confidence score
selected agent
response summary
status
error message
timestamp
```

The application does not expose update or delete operations for audit logs. This supports the append-only requirement.

Audit logs can be retrieved with:

```http
GET /audit
```

Optional user filter:

```http
GET /audit?user_id=user_001
```

The audit log helps trace how each request was classified, routed, and answered.

---

## 12. Error Handling and Fallback Behavior

The system includes defensive handling for LLM-related failures.

Possible failures include:

```text
missing API key
invalid API key
provider timeout
rate limit
invalid LLM JSON
empty LLM response
unsupported intent
```

The system avoids exposing raw Python stack traces to the user.

If specialist agent execution fails, the workflow returns a polite fallback response:

```text
I’m sorry, I could not complete the request right now. Please try again shortly or contact HR if the matter is urgent.
```

The failure is still recorded in the audit log with a safe error summary.

If intent classification fails, the system routes to the Clarification Agent with confidence `0.0`.

---

## 13. Testing Strategy

Automated tests are included using Pytest and FastAPI TestClient.

The tests cover:

```text
GET /health
GET /
POST /memory
GET /memory/{user_id}
GET /audit
POST /requests
```

The `/requests` test uses a mocked workflow instead of calling the real LLM. This avoids:

```text
external API dependency
network failures
rate limit issues
unnecessary LLM cost
non-deterministic test output
```

Manual testing was also performed for real LLM-based routing using example requests for:

```text
leave
scheduling
compliance
clarification
```

All four intent categories were successfully routed to the expected specialist agents.

---

## 14. Configuration

The system uses `.env` configuration.

Important variables:

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

The actual `.env` file is not committed to Git because it contains sensitive API credentials. A `.env.example` file is included for evaluator setup.

---

## 15. Security and Privacy Considerations

The project avoids committing sensitive local files.

Ignored files include:

```text
.env
.venv/
*.db
*.sqlite3
__pycache__/
.pytest_cache/
```

The API key is loaded only from environment configuration. It is not exposed in API responses.

The `/health` endpoint only returns whether the LLM is configured, not the key itself.

---

## 16. Trade-Offs

### 16.1 SQLite Instead of Production Database

SQLite was used because it was required by the challenge and is convenient for local evaluation. For production, PostgreSQL would be more appropriate.

### 16.2 Rule-Based Significance Scoring

The significance scoring system is deterministic and transparent. However, it may miss subtle user preferences. A production system could improve this using embeddings, semantic similarity, or learned scoring.

### 16.3 Simple Memory Retrieval

The current memory retrieval strategy returns recent STM and high-significance LTM records. A production system could use vector search and semantic ranking.

### 16.4 Mock HR Policies

The specialist agents use mock HR policy data. No real HRIS, calendar, leave-management, payroll, or legal system is integrated.

### 16.5 LLM Dependency

The system requires an LLM API key for full operation. This satisfies the AI challenge requirement, but it means runtime behavior depends on provider availability.

### 16.6 No Frontend

A frontend was not implemented because the challenge focused on backend REST endpoints, agent orchestration, memory, and audit logging. FastAPI Swagger UI provides a sufficient interface for testing.

---

## 17. Known Limitations

Current limitations:

```text
- No authentication or authorization
- No real HR system integration
- No real calendar integration
- No vector database
- No streaming responses
- No advanced retry policy per graph node
- No production-grade database migrations
- No role-based access control
```

These were intentionally excluded to keep the project focused and achievable within the challenge deadline.

---

## 18. Future Improvements

Possible future improvements:

```text
- Add authentication and user roles
- Add vector-based long-term memory retrieval
- Add embedding-based semantic memory search
- Add real HRIS integration
- Add calendar integration for scheduling
- Add leave approval workflow
- Add database migrations using Alembic
- Add Docker support
- Add observability and structured logging
- Add a lightweight frontend or CLI demo
- Add evaluation metrics for classification quality
```

---

## 19. Conclusion

The HR Agent Engine demonstrates a working LLM-powered multi-agent backend for HR automation. It uses FastAPI for API delivery, LangGraph for orchestration, SQLite for persistence, LLM-based intent classification, specialist sub-agents, two-tier memory, and append-only audit logging.

The system successfully handles request routing, memory injection, audit logging, and safe fallback behavior. The implementation prioritizes clarity, modularity, and evaluator-friendly local setup while documenting realistic trade-offs and limitations.