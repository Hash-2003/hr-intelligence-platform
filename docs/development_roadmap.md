# HR Intelligence Platform - Development Roadmap

## Project Vision

HR Intelligence Platform is an AI-powered backend platform for HR request intake, document-grounded reasoning, memory-aware agent orchestration, and auditable draft response generation.

The system will evolve from a technical challenge MVP into a more complete AI engineering platform demonstrating:

- LLM-powered intent classification
- LangGraph-based multi-agent orchestration
- HR document retrieval and extraction
- Email/webhook-triggered request intake
- Structured database design
- Auditability and human-in-the-loop review
- Production-oriented backend practices

---

## Current Baseline

The current system already includes:

- FastAPI backend
- LangGraph orchestration
- LLM-based intent classification
- Scheduling, Leave, Compliance, and Clarification agents
- Short-term and long-term memory
- Append-only audit logs
- SQLite persistence
- Safe LLM failure handling
- Pytest API tests
- Postman collection
- Technical documentation

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
email_events
draft_responses
```

Suggested purpose of each table:

| Table | Purpose |
|---|---|
| `users` | Stores user or requester records. |
| `hr_requests` | Stores HR cases created from API, email, or webhook input. |
| `agent_runs` | Stores each agent execution linked to an HR request. |
| `audit_logs` | Stores append-only trace records for observability and review. |
| `short_term_memory` | Stores recent request context. |
| `long_term_memory` | Stores durable user preferences and important context. |
| `documents` | Stores uploaded or registered HR documents. |
| `document_chunks` | Stores extracted and chunked text from documents. |
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

### Phase 6: Production Tooling

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

The next recommended implementation step is **PII and sensitive-data redaction before LLM calls**.

Rationale:

The platform now has request intake, webhook intake, draft review, auditability, explicit state validation, mock RBAC, and reviewer actor traceability. The largest remaining safety and production-readiness gap is privacy handling for HR data before it is sent to an external or hosted LLM provider.

Recommended first code changes:

1. Add a deterministic `PIIRedactionService`.
2. Redact common sensitive fields before LLM calls:
   - email addresses
   - phone numbers
   - employee IDs
   - national ID/NIC-like patterns
   - URLs
   - salary/payroll amounts where feasible
3. Preserve raw stored records for local backend traceability while sending sanitized prompt text to the LLM.
4. Add redaction metadata such as detected entity counts/types.
5. Avoid storing raw sensitive LLM prompts in audit details.
6. Add tests for redaction behavior and workflow integration.

This should be implemented before real email sending, production deployment, or integration with external HR/email systems.
