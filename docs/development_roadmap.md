# HR Intelligence Platform - Development Roadmap

## Project Vision

HR Intelligence Platform is an AI-powered backend platform for HR request intake, document-grounded reasoning, memory-aware agent orchestration, and auditable draft response generation.

The system is evolving from a technical challenge MVP into a more complete AI engineering platform demonstrating:

- LLM-powered intent classification
- LangGraph-based multi-agent orchestration
- Controlled HR document ingestion
- Traceable document-grounded retrieval
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
- Intent correction guardrails for obvious HR routing cases
- Scheduling, Leave, Compliance, and Clarification agents
- Short-term and long-term memory
- Append-only audit logs
- SQLite persistence
- Safe LLM failure handling
- Pytest API tests
- Postman collection
- Technical documentation
- HR request/case persistence
- Agent run persistence
- Request retrieval endpoints
- Controlled HR document ingestion from local policy files
- Document chunk storage
- Keyword-based HR policy retrieval
- Policy context injection into Leave and Compliance agents
- Persisted policy sources used by HR requests
- Policy source retrieval endpoint
- Email-like webhook intake
- Webhook `received_at` timestamp support
- Timezone-aware datetime context
- Deterministic leave date fact extraction
- Leave notice deadline validation
- Model configuration tested with multiple Groq-hosted models

---

## Target Platform Features

### Phase 1: Foundation Refactor

Goal: prepare the system for larger platform extensions.

Completed:

- Added HR request model
- Added agent run model
- Added request status tracking
- Updated `/requests` pipeline to persist HR request records
- Added API endpoints to retrieve requests and agent runs
- Added tests for HR request and agent run retrieval endpoints

Remaining:

- Improve status transition model
- Add richer request filtering
- Add pagination metadata
- Add database migrations

---

### Phase 2: Document Ingestion

Goal: allow the system to ingest controlled HR policy documents and store reusable text chunks.

Completed:

- Added controlled local HR document directory: `data/hr_documents/`
- Added sample HR policy documents:
  - Leave policy
  - Overtime policy
  - Code of conduct
- Added `documents` table
- Added `document_chunks` table
- Added local document ingestion script
- Added SHA-256 content hashing for change detection
- Added text chunking logic
- Added document retrieval endpoints
- Added tests for document ingestion and retrieval

Remaining:

- Add support for PDF or DOCX documents
- Add document versioning
- Add document category/filter metadata
- Add admin-only document upload later if needed

---

### Phase 3: Document-Grounded Agent Responses

Goal: use HR policy context inside agent prompts and make retrieved sources traceable.

Completed:

- Added keyword-based policy chunk retrieval
- Added lightweight token normalization for keyword matching
- Injected retrieved policy context into agent prompts
- Improved Leave and Compliance Agent prompts for policy-grounded answers
- Added intent correction guardrails for obvious HR routing errors
- Persisted policy source metadata for each HR request
- Added endpoint to retrieve policy sources used by a request:

```http
GET /hr-requests/{request_id}/policy-sources
```

- Added tests for policy source retrieval

Remaining:

- Improve retrieval ranking
- Add source-aware response formatting
- Add embedding-based semantic retrieval
- Add retrieval quality evaluation tests
- Persist full retrieved context snapshots if needed for deeper auditability

---

### Phase 4: Webhook Intake

Goal: support external request triggers.

Completed:

- Added `/webhooks/email` endpoint
- Added email event persistence
- Converted incoming email-like events into HR requests
- Reused the existing LangGraph workflow for webhook requests
- Linked processed email events to generated HR requests
- Used webhook `received_at` as the reference timestamp for date-sensitive reasoning
- Added tests for webhook validation and metadata passing

Remaining:

- Add richer email event retrieval endpoints
- Add n8n/Gmail integration guide
- Add retry/failure status handling for webhook processing request processing through the backend.

---

### Phase 5: Draft Response Workflow

Goal: make generated responses reviewable before any sensitive HR communication is sent.

Planned features:

- Add `draft_responses` table
- Generate draft HR responses linked to HR requests
- Add endpoints to list, retrieve, update, approve, and reject drafts
- Add request status transitions such as `draft_generated`, `needs_review`, `approved`, `rejected`, and `closed`
- Keep audit logs for review actions

The system should not automatically send emails in the first version.

Expected outcome:

- The system supports human-in-the-loop review rather than automatically sending sensitive HR responses.

---

### Phase 6: Improved Platform Schema

Goal: move from a simple local assessment schema toward a more complete platform schema.

Current and planned tables:

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
| `agent_runs` | Stores each agent execution linked to an HR request. |
| `audit_logs` | Stores append-only trace records for observability and review. |
| `short_term_memory` | Stores recent request context. |
| `long_term_memory` | Stores durable user preferences and important context. |
| `documents` | Stores controlled HR documents. |
| `document_chunks` | Stores extracted and chunked text from documents. |
| `request_policy_sources` | Stores policy chunks used by each HR request. |
| `email_events` | Stores incoming email or webhook events. |
| `draft_responses` | Stores generated responses awaiting review. |

---

### Phase 7: RAG and Semantic Search Improvements

Goal: improve retrieval quality beyond keyword matching.

Possible options:

- ChromaDB for local vector storage
- PostgreSQL with pgvector
- FAISS for local retrieval
- Hybrid retrieval combining keywords and embeddings

Planned improvements:

- Generate embeddings for document chunks
- Retrieve chunks by semantic similarity
- Combine semantic scores with keyword scores
- Add source-aware response citations
- Add retrieval evaluation test cases

Current implementation uses keyword-based retrieval because it is transparent, easy to debug, and suitable for the initial controlled policy document set.

---

### Phase 8: Safety-Sensitive Request Handling

Goal: avoid treating crisis, self-harm, or emergency messages as normal HR requests.

Planned features:

- Add a dedicated Safety Agent for crisis-sensitive or non-HR emergency messages
- Detect safety-sensitive messages before normal HR routing
- Return supportive, non-diagnostic, non-graphic responses
- Recommend immediate real-world support or emergency help when appropriate
- Avoid routing crisis messages to Leave, Scheduling, Compliance, or generic Clarification agents
- Record only minimal safe audit metadata for sensitive safety cases

This phase should be handled carefully and separately from standard HR policy automation.

---

### Phase 9: Production Readiness Improvements

Goal: improve deployment, maintainability, and operational quality.

Planned improvements:

- Alembic database migrations
- Dockerfile
- Docker Compose setup
- PostgreSQL support
- Structured logging
- Request IDs in logs
- Better error models
- Environment-specific settings
- CI workflow for tests
- Improved test database isolation
- Basic observability and health diagnostics
- Add PII and sensitive-data redaction before LLM calls

Expected outcome:

- The project becomes easier to deploy, test, and extend in a realistic engineering environment.

### Date-Sensitive Leave Handling

Goal: avoid relying on the LLM for calendar arithmetic and leave notice validation.

Completed:

- Added timezone configuration through `APP_TIMEZONE`
- Added timezone-aware datetime context
- Added deterministic leave date fact extraction
- Supported common relative date phrases such as `next Monday`, `tomorrow`, and `a week after next Monday`
- Added leave duration extraction for phrases like `for 2 days`
- Calculated latest standard submission date using backend logic
- Calculated notice status as `missed`, `deadline_today`, `not_missed`, or `unknown`
- Passed resolved leave date facts to the Leave Agent
- Added tests for leave date resolution edge cases

Remaining:

- Support more natural date expressions
- Support public holidays/weekends if HR policy requires business-day calculations
- Add richer date parser or controlled date extraction layer if needed
---


## Design Principles

- API-first backend design
- Controlled HR document knowledge base
- Human-in-the-loop for HR decisions
- No automatic sending of sensitive HR responses initially
- Transparent audit trail
- Traceable document-grounded responses
- Clear separation between orchestration, agents, memory, documents, retrieval, and persistence
- Safe fallback behavior for LLM failures
- Avoid exposing sensitive credentials or raw internal errors
- Build incrementally, with working checkpoints after each phase

---

## Immediate Next Step

The next implementation step should be **Phase 4: Email/Webhook Intake**.

Recommended first code changes:

1. Add `EmailEvent` SQLAlchemy model.
2. Add corresponding Pydantic schemas.
3. Add `EmailEventService`.
4. Add `/webhooks/email` endpoint for generic email-like payloads.
5. Convert incoming webhook payloads into persistent HR requests.
6. Run the existing LangGraph workflow for webhook-created requests.
7. Store generated response as a draft rather than sending anything automatically.
8. Add tests for webhook intake and request creation.

This should be implemented before Gmail or n8n integration so that the backend remains testable without external OAuth or automation dependencies.

