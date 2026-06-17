# HR Intelligence Platform - Development Roadmap

## Project Vision

HR Intelligence Platform is an AI-powered backend platform for HR request intake, document-grounded reasoning, memory-aware agent orchestration, deterministic leave handling, risk-based Human-in-the-Loop review, mock RBAC-protected reviewer operations, privacy-aware LLM prompting, and auditable draft response generation.

The system will evolve from a technical challenge MVP into a more complete AI engineering platform demonstrating:

- LLM-powered intent classification
- LangGraph-based multi-agent orchestration
- HR document retrieval and extraction
- Email/webhook-triggered request intake
- Deterministic date-sensitive leave handling
- Risk-based Human-in-the-Loop review
- Mock RBAC for reviewer/admin operations
- PII redaction before LLM provider calls
- Structured database design
- Auditability and operational traceability
- Production-oriented backend practices

---

## Current Baseline

The current system already includes:

- FastAPI backend
- LangGraph orchestration
- LLM-based intent classification
- Intent correction guardrails for high-signal HR requests
- Scheduling, Leave, Compliance, and Clarification agents
- Short-term and long-term memory
- Append-only audit logs
- SQLite persistence
- Safe LLM failure handling
- Pytest API and service tests
- Postman collection
- Technical documentation
- HR request/case persistence
- Agent run persistence
- Controlled HR document ingestion from local policy files
- Document chunk storage
- Keyword-based HR policy retrieval
- Policy source traceability for HR requests
- Email-like webhook intake
- Email event persistence and filtering
- Timezone-aware datetime context through `APP_TIMEZONE`
- Deterministic leave date fact extraction
- Leave notice deadline validation
- Human-reviewable draft response workflow
- Risk-based Human-in-the-Loop review metadata
- Draft approval, rejection, and send simulation endpoints
- Explicit draft state transition validation with `409 Conflict` responses
- Generic audit event metadata and draft lifecycle audit events
- Reviewer/admin actor metadata in draft lifecycle audit events
- Mock header-based RBAC for draft, audit, and email-event operations
- Filterable and paginated operational list endpoints
- Centralized domain constants and enums
- Deterministic PII redaction service
- LLM user prompts redacted before provider calls
- Specialist agent PII redaction metadata persisted in `agent_runs`


---

## Target Platform Features

### 1. HR Request Management

Introduce a dedicated HR request/case model.

Planned features:

- Create HR requests from API input
- Store source type: API, email, webhook
- Track request status
- Track classified intent and confidence
- Store selected agent and response
- Support review and resolution states

Potential statuses:

```text
new
classified
draft_generated
needs_review
approved
rejected
closed
failed
```

---

### 2. Document-Aware HR Reasoning

Add HR policy document ingestion and retrieval.

Planned features:

- Upload or register HR policy documents
- Extract text from documents
- Split text into chunks
- Store document chunks
- Retrieve relevant chunks during agent execution
- Inject retrieved policy context into LLM prompts
- Include source references in agent responses

Initial documents:

- Leave policy
- Overtime policy
- Employee handbook
- Code of conduct
- Remote work policy
- Expense reimbursement policy

---

### 3. Email/Webhook Intake

Add an intake mechanism for HR-related emails or external automation tools.

Planned features:

- Webhook endpoint for incoming email-like events
- Store email sender, subject, body, and timestamp
- Classify email intent
- Create an HR request automatically
- Generate a draft response
- Keep response as draft for human review

Initial implementation should use a generic webhook before integrating Gmail or n8n.

---

### 4. Draft Response Workflow

Add human-in-the-loop draft response management.

Planned features:

- Generate draft HR responses
- Store draft response linked to HR request
- Review draft before sending
- Update draft manually
- Mark draft as approved or rejected

The system should not automatically send emails in the first version.

---

### 5. Improved Database Schema

Move from simple assessment tables to a more complete platform schema.

Planned tables:

```text
users
hr_requests
agent_runs
audit_logs
short_term_memory
long_term_memory
documents
document_chunks
request_policy_sources
email_events
draft_responses
```

Suggested purpose of each table:

| Table | Purpose |
|---|---|
| `users` | Stores user or requester records. |
| `hr_requests` | Stores HR cases created from API, email, or webhook input. |
| `agent_runs` | Stores each agent execution linked to an HR request, including optional PII redaction metadata. |
| `audit_logs` | Stores append-only trace records for observability and review. |
| `short_term_memory` | Stores recent request context. |
| `long_term_memory` | Stores durable user preferences and important context. |
| `documents` | Stores uploaded or registered HR documents. |
| `document_chunks` | Stores extracted and chunked text from documents. |
| `request_policy_sources` | Stores policy chunks used by each HR request. |
| `email_events` | Stores incoming email or webhook events. |
| `draft_responses` | Stores generated responses awaiting review. |

---

### 6. RAG and Semantic Search

Future document retrieval can be improved using embeddings.

Possible options:

- ChromaDB for local vector storage
- PostgreSQL with pgvector
- FAISS for local retrieval

Initial implementation can use keyword-based retrieval before adding embeddings. This allows the document workflow to be built and tested before introducing vector database complexity.

---

### 7. Production Readiness Improvements

Planned improvements:

- Alembic database migrations
- Docker support
- Structured logging
- Better error models
- Request IDs in logs
- Environment-specific settings
- Improved tests
- CI workflow
- PostgreSQL support
- Alembic migration for `agent_runs.pii_redaction_counts`
- Stronger privacy controls for raw email/request storage

---

## Implementation Phases

### Phase 1: Foundation Refactor

Goal: prepare the system for larger platform extensions.

Tasks:

- Add HR request model
- Add agent run model
- Keep audit log append-only
- Add request status tracking
- Update `/requests` pipeline to persist HR request records
- Add API endpoints to retrieve requests

Expected outcome:

- Every incoming request becomes a persistent HR case.
- Every agent execution can be traced through an agent run record.
- Audit logs remain append-only and independent from operational request records.

---

### Phase 2: Document Ingestion

Goal: allow the system to store HR documents and extract text.

Tasks:

- Add document and document chunk tables
- Add document upload endpoint
- Add text extraction for `.txt` and `.md`
- Add simple chunking logic
- Add document retrieval service

Expected outcome:

- HR policy documents can be registered in the system.
- Extracted text can be stored and retrieved for later agent use.

---

### Phase 3: Document-Grounded Agent Responses

Goal: use HR policy context inside agent prompts.

Tasks:

- Retrieve relevant document chunks based on user message
- Inject retrieved policy context into Leave and Compliance agents
- Store which chunks were used
- Add source-aware response summaries

Expected outcome:

- Leave and Compliance Agent responses become grounded in stored HR documents instead of only mock policy text.

---

### Phase 4: Webhook Intake

Goal: support external request triggers.

Tasks:

- Add `/webhooks/email` endpoint
- Store incoming email event
- Convert email into HR request
- Run existing LangGraph workflow
- Generate draft response

Expected outcome:

- External tools such as n8n or email parsers can trigger HR request processing through the backend.

---

### Phase 5: Human Review Workflow

Goal: make generated responses reviewable.

Tasks:

- Add draft response table
- Add endpoints to list, update, approve, and reject drafts
- Add request status transitions
- Keep audit log for review actions

Expected outcome:

- The system supports human-in-the-loop review rather than automatically sending sensitive HR responses.

---

### Phase 6: Privacy and PII Redaction

Goal: minimize sensitive HR data exposure when using hosted or external LLM providers.

Completed:

- Added deterministic `PIIRedactionService`
- Redacted sensitive user prompt content at the centralized `LLMService` boundary
- Added redaction support for:
  - email addresses
  - phone numbers
  - URLs
  - Sri Lankan NIC-like national IDs
  - employee IDs and employee numbers
  - salary/payroll amounts
- Tracked redaction counts in `LLMService`
- Persisted specialist agent redaction metadata in `agent_runs.pii_redaction_counts`
- Added tests for redaction behavior, LLM boundary redaction, and redaction metadata persistence

Current design:

```text
Raw input may be stored internally for HR traceability
    ↓
User prompt is redacted before LLM provider call
    ↓
Only safe redaction count metadata is persisted for specialist agent runs
```

Remaining:

- Add name and address redaction if needed
- Add consistent pseudonymization where preserving identity relationships matters
- Consider encrypted storage for raw HR/email content
- Add a dedicated `llm_call_logs` table if classifier-level and auxiliary LLM-call observability is required
- Decide whether redacted prompt snapshots are necessary or whether counts-only metadata is sufficient
- Extend privacy tests around webhook-generated requests and high-risk HR topics

---

### Phase 7: Production Tooling

Goal: improve deployment and maintainability.

Tasks:

- Add Alembic
- Add Dockerfile
- Add docker-compose
- Add PostgreSQL option
- Add CI test workflow
- Improve logging and observability

Expected outcome:

- The project becomes easier to deploy, test, and extend in a realistic engineering environment.

---

## Design Principles

- API-first backend design
- Human-in-the-loop for HR decisions
- No automatic sending of sensitive HR responses initially
- Transparent audit trail
- Clear separation between orchestration, agents, memory, documents, and persistence
- Safe fallback behavior for LLM failures
- Avoid exposing sensitive credentials or raw internal errors
- Build incrementally, with working checkpoints after each phase

---

## Immediate Next Step

The next recommended implementation step is **Alembic database migrations**.

Rationale:

The system now has a growing schema with operational tables, draft lifecycle states, RBAC-related audit metadata, and `agent_runs.pii_redaction_counts`. Since SQLite will not automatically update existing tables when model columns are added, migrations are becoming necessary for reliable development and deployment.

Recommended first code changes:

1. Add Alembic.
2. Generate an initial migration from the current SQLAlchemy models.
3. Add a migration for `agent_runs.pii_redaction_counts` if the baseline database already exists.
4. Document migration commands in the README.
5. Update local setup instructions so developers run migrations instead of relying only on automatic table creation.

This should be implemented before more schema-heavy features such as real users, production authentication, email delivery logs, or a dedicated `llm_call_logs` table.
