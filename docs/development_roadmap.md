# HR Intelligence Platform - Development Roadmap

## Project Vision

HR Intelligence Platform is an AI-powered backend platform for HR request intake, document-grounded reasoning, memory-aware agent orchestration, deterministic leave-date handling, risk-based Human-in-the-Loop review, and auditable draft response generation.

The system is evolving from a technical challenge MVP into a more complete AI engineering platform demonstrating:

- LLM-powered intent classification
- LangGraph-based multi-agent orchestration
- Controlled HR document ingestion
- Traceable document-grounded retrieval
- Email/webhook-triggered request intake
- Deterministic business-rule handling for date-sensitive leave requests
- Risk-based Human-in-the-Loop review
- Structured database design
- Auditability and production-oriented backend practices

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
- Pytest API and service tests
- Postman collection
- Technical documentation
- HR request/case persistence
- Agent run persistence
- Request retrieval endpoints
- Controlled HR document ingestion from local policy files
- Document chunk storage
- Keyword-based HR policy retrieval
- Policy context injection into agents
- Persisted policy sources used by HR requests
- Policy source retrieval endpoint
- Email-like webhook intake
- Email event persistence
- Webhook `received_at` timestamp support
- Timezone-aware datetime context through `APP_TIMEZONE`
- Deterministic leave date fact extraction
- Leave notice deadline validation
- Model configuration tested with multiple Groq-hosted models
- Human-reviewable draft response workflow
- Draft approval and rejection endpoints
- Risk-based Human-in-the-Loop review metadata
- Hybrid `ReviewDecisionService` with deterministic rules and optional LLM-assisted classification for ambiguous soft-risk cases
- Isolated test database configuration
- Pagination metadata for `/drafts`, `/audit`, `/email-events`, and `/hr-requests`
- Audit event filtering
- Draft queue filtering
- Generic audit event metadata and draft lifecycle audit events
- Draft approval, rejection, and send simulation endpoints
- Email-formatted draft responses
- Email event retrieval and filtering endpoints

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
- Expand pagination metadata to secondary/nested endpoints if needed
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
- Updated webhook response to include generated `draft_id` and review decision metadata
- Added tests for webhook validation and metadata passing
- Added email event retrieval and filtering endpoints
- Added paginated `/email-events` responses with `{ items, total, limit, offset }`

Remaining:

- Add richer retry/failure status handling for email/webhook event processing
- Add n8n/Gmail integration guide
- Add retry/failure status handling for webhook processing
- Add email-source authentication/signature validation for real integrations

---

### Phase 5: Date-Sensitive Leave Handling

Goal: avoid relying on the LLM for calendar arithmetic and leave notice validation.

Completed:

- Added timezone configuration through `APP_TIMEZONE`
- Added timezone-aware datetime context
- Added deterministic leave date fact extraction
- Supported common relative date phrases such as:
  - `next Monday`
  - `tomorrow`
  - `today`
  - `a week after next Monday`
  - `one week after next Monday`
- Added leave duration extraction for phrases like `for 2 days`
- Calculated latest standard submission date using backend logic
- Calculated notice status as `missed`, `deadline_today`, `not_missed`, or `unknown`
- Passed resolved leave date facts to the Leave Agent
- Simplified the Leave Agent so the LLM explains resolved facts instead of calculating dates
- Added tests for leave date resolution edge cases

Remaining:

- Support more natural date expressions
- Support public holidays/weekends if HR policy requires business-day calculations
- Add richer date parser or controlled date extraction layer if needed
- Support locale-specific date formats if required

---

### Phase 6: Risk-Based HITL Draft Response Workflow

Goal: prevent AI-generated HR responses from being treated as final outputs without review control.

Completed:

- Added hybrid `ReviewDecisionService`
- Added deterministic review rules for:
  - safety-sensitive requests
  - legal or whistleblowing terms
  - security/data-protection concerns
  - workplace misconduct concerns
  - salary/payroll issues
  - medical and sensitive HR topics
- Added optional LLM-assisted classification for ambiguous soft-risk cases
- Added safe fallback to human review when LLM review classification fails
- Added `draft_responses` table
- Added draft response persistence for webhook-generated HR responses
- Added review metadata to drafts:
  - `review_action`
  - `review_required`
  - `review_priority`
  - `review_reason`
  - `review_decision_source`
- Added draft lifecycle endpoints:
  - `GET /drafts`
  - `GET /drafts/{draft_id}`
  - `PATCH /drafts/{draft_id}`
  - `POST /drafts/{draft_id}/approve`
  - `POST /drafts/{draft_id}/reject`
- Updated webhook response to return `draft_id` and review decision metadata
- Added tests for review decision behavior and draft workflow behavior
- Added email-formatted draft response bodies through a dedicated formatter
- Added draft send simulation after approval
- Added generic audit events for draft lifecycle actions:
  - `draft_created`
  - `draft_updated`
  - `draft_approved`
  - `draft_rejected`
  - `draft_sent`
- Added draft queue filtering by status, review requirement, review priority, review action, and recipient email
- Added paginated `/drafts` responses with `{ items, total, limit, offset }`

Remaining:

- Add real email sending only after approval
- Add authentication and role-based access control for draft review
- Add dashboard/UI for HR reviewers
- Add PII redaction before LLM calls
- Add reviewer identity tracking once authentication is available

---

### Phase 7: Improved Platform Schema

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
| `draft_responses` | Stores generated responses awaiting review and review decision metadata. |

Remaining:

- Add Alembic migrations before schema changes become larger
- Add stronger status transition constraints
- Add user/reviewer identity tracking
- Add stronger query/index design for growing operational tables

---

### Phase 8: Operational Review, Filtering, and Pagination

Goal: make the backend easier to inspect, debug, and connect to a future HR reviewer dashboard.

Completed:

- Added generic audit event fields:
  - `event_type`
  - `resource_type`
  - `resource_id`
  - `details_json`
- Added draft lifecycle audit events:
  - `draft_created`
  - `draft_updated`
  - `draft_approved`
  - `draft_rejected`
  - `draft_sent`
- Added audit log filtering by:
  - user ID
  - request ID
  - event type
  - resource type
  - resource ID
  - status
- Added email event retrieval and filtering by:
  - status
  - sender email
  - source
  - linked request ID
- Added draft queue filtering by:
  - status
  - review required
  - review priority
  - review action
  - recipient email
- Added pagination metadata for:
  - `GET /drafts`
  - `GET /audit`
  - `GET /email-events`
  - `GET /hr-requests`
- Standardized list response shape:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Remaining:

- Add pagination metadata to secondary/nested endpoints if needed
- Add sorting controls if required by a future dashboard
- Add stronger database indexing before large datasets
- Add reviewer identity fields once authentication is implemented

---

### Phase 9: RAG and Semantic Search Improvements

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

### Phase 10: Safety-Sensitive Request Handling

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

### Phase 11: Production Readiness Improvements

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
- Standardized pagination metadata for main operational endpoints
- Basic observability and health diagnostics
- PII and sensitive-data redaction before LLM calls
- Authentication and role-based authorization
- Secure handling of raw email/webhook content
- Retention policy for sensitive HR data

Expected outcome:

- The project becomes easier to deploy, test, and extend in a realistic engineering environment.

---

## Future Privacy Hardening: PII Redaction Before LLM Calls

Planned feature:

- Add a PII redaction layer before sending user messages, email bodies, or document excerpts to the LLM
- Redact or pseudonymize sensitive fields such as names, emails, phone numbers, employee IDs, addresses, salary details, and medical information
- Keep raw events stored securely while sending only sanitized prompt content to the LLM
- Avoid storing raw sensitive prompts in audit logs
- Store redacted summaries and trace metadata for debugging and review
- Consider hashing stable identifiers for internal matching where appropriate
- Keep human review for sensitive HR cases such as harassment, medical leave, disciplinary concerns, and payroll issues

Reason:

HR systems process sensitive employee information. Even if the LLM is self-hosted or enterprise-hosted, the platform should minimize unnecessary exposure of personal data and avoid leaking sensitive information through prompts, logs, or audit records.

---

## Design Principles

- API-first backend design
- Controlled HR document knowledge base
- Risk-based Human-in-the-Loop review instead of mandatory review for every case
- No automatic sending of sensitive HR responses initially
- Transparent audit trail
- Traceable document-grounded responses
- Deterministic code for business-critical calculations such as leave dates and notice deadlines
- LLMs used for language generation, classification support, and policy-grounded explanations rather than final business-rule authority
- Clear separation between orchestration, agents, memory, documents, retrieval, review decisions, drafts, and persistence
- Safe fallback behavior for LLM failures
- Avoid exposing sensitive credentials or raw internal errors
- Build incrementally, with working checkpoints after each phase

---

## Immediate Next Step

The next recommended implementation step is **status transition validation and domain constants/enums**.

Rationale:

The system now has several important domain states:

```text
draft → approved → sent
draft → rejected
review_action: auto_response, review_optional, review_required, escalated
review_priority: low, medium, high, critical
email_event.status: received, processed
```

These values are currently useful, but they should become more centralized and harder to mistype as the project grows.

Recommended first code changes:

1. Add centralized constants or enums for draft statuses, review actions, review priorities, and email event statuses.
2. Update services to use these constants instead of repeated string literals.
3. Add explicit state transition validation for draft lifecycle actions.
4. Return clearer errors for invalid state transitions.
5. Add tests for valid and invalid transitions.

This should be implemented before real email sending, authentication, or frontend integration because the workflow state model should be reliable first.
