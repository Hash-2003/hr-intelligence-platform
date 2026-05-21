from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database import Document, DocumentChunk


@dataclass
class RetrievedPolicyChunk:
    """Relevant policy chunk selected for agent prompt context."""

    document_id: int
    document_title: str
    filename: str
    chunk_id: int
    chunk_index: int
    content: str
    score: int


class DocumentRetrievalService:
    """Keyword-based retrieval service for HR policy context."""

    def __init__(self, db: Session):
        self.db = db

    def retrieve_policy_context(
        self,
        query: str,
        intent: str | None,
        limit: int = 3,
    ) -> tuple[str, list[RetrievedPolicyChunk]]:
        """Retrieve relevant HR document chunks and format them for prompt injection."""
        retrieved_chunks = self.retrieve_relevant_chunks(
            query=query,
            intent=intent,
            limit=limit,
        )

        if not retrieved_chunks:
            return "No relevant HR policy context found.", []

        context_lines = ["Relevant HR policy context:"]

        for item in retrieved_chunks:
            context_lines.append(
                f"- Source: {item.document_title} ({item.filename}), "
                f"chunk {item.chunk_index}\n"
                f"  Content: {item.content}"
            )

        return "\n".join(context_lines), retrieved_chunks

    def retrieve_relevant_chunks(
        self,
        query: str,
        intent: str | None,
        limit: int = 3,
    ) -> list[RetrievedPolicyChunk]:
        """Retrieve relevant chunks using transparent keyword scoring."""
        query_terms = self._build_query_terms(query=query, intent=intent)

        rows = (
            self.db.query(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .all()
        )

        scored: list[RetrievedPolicyChunk] = []

        for chunk, document in rows:
            score = self._score_chunk(
                text=f"{document.title} {document.filename} {chunk.content}",
                query_terms=query_terms,
            )

            if score > 0:
                scored.append(
                    RetrievedPolicyChunk(
                        document_id=document.id,
                        document_title=document.title,
                        filename=document.filename,
                        chunk_id=chunk.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        score=score,
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)

        return scored[:limit]

    def _build_query_terms(self, query: str, intent: str | None) -> set[str]:
        """Build retrieval terms from user query and classified intent."""
        terms = self._tokenize(query)

        intent_terms = {
            "leave": {
                "leave",
                "annual",
                "sick",
                "casual",
                "absence",
                "medical",
                "certificate",
                "certification",
                "hris",
                "approval",
                "approve",
                "approved",
                "request",
                "requested",
                "requesting",
                "vacation",
                "accrued",
                "unpaid",
                "emergency",
                "manager",
                "unforeseen",
                "balance",
                "illness",
                "injury",
            },
            "scheduling": {
                "meeting",
                "interview",
                "schedule",
                "reschedule",
                "calendar",
                "appointment",
                "shift",
            },
            "compliance": {
                "policy",
                "overtime",
                "approval",
                "approve",
                "approved",
                "salary",
                "contract",
                "conduct",
                "harassment",
                "harassed",
                "discrimination",
                "discriminated",
                "confidential",
                "complaint",
                "complaints",
                "retaliation",
                "timesheet",
                "payroll",
                "workload",
                "escalation",
                "dispute",
                "integrity",
                "misconduct",
                "investigation",
                "investigations",
                "inclusive",
                "proprietary",
                "security",
            },
            "clarification": set(),
        }

        terms.update(intent_terms.get(intent or "", set()))

        return {
            self._normalize_token(term)
            for term in terms
        }

    @staticmethod
    def _score_chunk(text: str, query_terms: set[str]) -> int:
        """Score a chunk by keyword overlap."""
        text_terms = DocumentRetrievalService._tokenize(text)
        overlap = query_terms.intersection(text_terms)

        return len(overlap)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Convert text into normalized lowercase word tokens."""
        cleaned = []

        for char in text.lower():
            if char.isalnum():
                cleaned.append(char)
            else:
                cleaned.append(" ")

        return {
            DocumentRetrievalService._normalize_token(token)
            for token in "".join(cleaned).split()
            if len(token) >= 3
        }

    @staticmethod
    def _normalize_token(token: str) -> str:
        """Normalize simple word variants for keyword retrieval."""
        replacements = {
            "approved": "approval",
            "approve": "approval",
            "approving": "approval",
            "requests": "request",
            "requested": "request",
            "requesting": "request",
            "worked": "work",
            "working": "work",
            "harassed": "harassment",
            "harassing": "harassment",
            "discriminated": "discrimination",
            "discriminating": "discrimination",
            "complaints": "complaint",
            "investigations": "investigation",
            "certificates": "certificate",
            "certification": "certificate",
        }

        return replacements.get(token, token)