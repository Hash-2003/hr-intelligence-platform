from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.clarification_agent import ClarificationAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.leave_agent import LeaveAgent
from app.agents.scheduling_agent import SchedulingAgent
from app.config import get_settings
from app.services.audit_service import AuditService
from app.services.intent_classifier import IntentClassifier
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMServiceError
from app.services.hr_request_service import HRRequestService
from app.services.document_retrieval_service import DocumentRetrievalService


class WorkflowState(TypedDict, total=False):
    """State shared across LangGraph workflow nodes."""

    request_id: str
    user_id: str
    message: str
    memory_context: str
    memory_used: bool
    policy_context: str
    policy_sources_used: list[dict]
    intent: str
    confidence: float
    reasoning_summary: str
    selected_agent: str
    response: str
    status: str
    error_message: str | None


class HRWorkflow:
    """LangGraph workflow for HR request orchestration."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.memory_service = MemoryService(db)
        self.audit_service = AuditService(db)
        self.hr_request_service = HRRequestService(db)
        self.document_retrieval_service = DocumentRetrievalService(db)
        self.intent_classifier = IntentClassifier()

        self.scheduling_agent = SchedulingAgent()
        self.leave_agent = LeaveAgent()
        self.compliance_agent = ComplianceAgent()
        self.clarification_agent = ClarificationAgent()

        self.graph = self._build_graph()

    def run(self, user_id: str, message: str) -> WorkflowState:
        """Run the workflow for one user request."""
        request_id = str(uuid4())

        self.hr_request_service.create_request(
            request_id=request_id,
            user_id=user_id,
            message=message,
            source_type="api",
        )

        initial_state: WorkflowState = {
            "request_id": request_id,
            "user_id": user_id,
            "message": message,
            "status": "success",
            "error_message": None,
        }

        return self.graph.invoke(initial_state)

    def _build_graph(self):
        """Build and compile the LangGraph state graph."""
        graph = StateGraph(WorkflowState)

        graph.add_node("load_memory", self._load_memory)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("scheduling_agent", self._run_scheduling_agent)
        graph.add_node("leave_agent", self._run_leave_agent)
        graph.add_node("compliance_agent", self._run_compliance_agent)
        graph.add_node("clarification_agent", self._run_clarification_agent)
        graph.add_node("retrieve_policy_context", self._retrieve_policy_context)
        graph.add_node("save_memory", self._save_memory)
        graph.add_node("write_audit", self._write_audit)

        graph.set_entry_point("load_memory")

        graph.add_edge("load_memory", "classify_intent")

        graph.add_edge("classify_intent", "retrieve_policy_context")

        graph.add_conditional_edges(
            "retrieve_policy_context",
            self._route_by_intent,
            {
                "scheduling": "scheduling_agent",
                "leave": "leave_agent",
                "compliance": "compliance_agent",
                "clarification": "clarification_agent",
            },
        )

        graph.add_edge("scheduling_agent", "save_memory")
        graph.add_edge("leave_agent", "save_memory")
        graph.add_edge("compliance_agent", "save_memory")
        graph.add_edge("clarification_agent", "save_memory")

        graph.add_edge("save_memory", "write_audit")
        graph.add_edge("write_audit", END)

        return graph.compile()

    def _load_memory(self, state: WorkflowState) -> WorkflowState:
        """Load STM and LTM context for the request."""
        memory_context, memory_used = self.memory_service.build_memory_context(
            user_id=state["user_id"]
        )

        return {
            **state,
            "memory_context": memory_context,
            "memory_used": memory_used,
        }

    def _classify_intent(self, state: WorkflowState) -> WorkflowState:
        """Classify the request intent using the LLM classifier."""
        result = self.intent_classifier.classify(
            message=state["message"],
            memory_context=state["memory_context"],
        )

        return {
            **state,
            "intent": result.intent,
            "confidence": result.confidence,
            "reasoning_summary": result.reasoning_summary,
        }

    def _retrieve_policy_context(self, state: WorkflowState) -> WorkflowState:
        """Retrieve relevant HR policy context for agent prompt injection."""
        policy_context, sources = self.document_retrieval_service.retrieve_policy_context(
            query=state["message"],
            intent=state.get("intent"),
            limit=3,
        )

        policy_sources_used = [
            {
                "document_id": source.document_id,
                "document_title": source.document_title,
                "filename": source.filename,
                "chunk_id": source.chunk_id,
                "chunk_index": source.chunk_index,
                "score": source.score,
            }
            for source in sources
        ]

        return {
            **state,
            "policy_context": policy_context,
            "policy_sources_used": policy_sources_used,
        }

    @staticmethod
    def _route_by_intent(state: WorkflowState) -> str:
        """Return the next graph branch based on classified intent."""
        intent = state.get("intent", "clarification")

        if intent in {"scheduling", "leave", "compliance"}:
            return intent

        return "clarification"

    def _run_agent_safely(
            self,
            state: WorkflowState,
            agent,
    ) -> WorkflowState:
        """Run a specialist agent and safely handle LLM failures."""
        try:
            response = agent.run(
                user_message=state["message"],
                memory_context=state["memory_context"],
                policy_context=state.get(
                    "policy_context",
                    "No relevant HR policy context found.",
                ),
            )

            return {
                **state,
                "selected_agent": agent.name,
                "response": response,
            }

        except LLMServiceError as exc:
            return {
                **state,
                "selected_agent": agent.name,
                "response": self._safe_failure_response(),
                "status": "failed",
                "error_message": str(exc),
            }

    def _run_scheduling_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the scheduling specialist agent."""
        return self._run_agent_safely(state, self.scheduling_agent)

    def _run_leave_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the leave specialist agent."""
        return self._run_agent_safely(state, self.leave_agent)

    def _run_compliance_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the compliance specialist agent."""
        return self._run_agent_safely(state, self.compliance_agent)

    def _run_clarification_agent(self, state: WorkflowState) -> WorkflowState:
        """Run the clarification specialist agent."""
        return self._run_agent_safely(state, self.clarification_agent)

    def _save_memory(self, state: WorkflowState) -> WorkflowState:
        """Save recent request context and promote significant items to LTM."""
        user_id = state["user_id"]
        message = state["message"]
        intent = state.get("intent")

        self.memory_service.add_short_term_memory(
            user_id=user_id,
            content=f"User said: {message}",
            intent=intent,
        )

        significance = self.memory_service.score_significance(
            message=message,
            intent=intent,
        )

        if significance >= self.settings.ltm_significance_threshold:
            self.memory_service.add_long_term_memory(
                user_id=user_id,
                content=f"Important user context: {message}",
                significance_score=significance,
            )

        return state

    def _write_audit(self, state: WorkflowState) -> WorkflowState:
        """Write one append-only audit log entry."""
        self.hr_request_service.update_request_result(
            request_id=state["request_id"],
            intent=state.get("intent"),
            confidence=state.get("confidence"),
            selected_agent=state.get("selected_agent"),
            response=state.get("response"),
            status=state.get("status", "success"),
            error_message=state.get("error_message"),
        )

        if state.get("selected_agent"):
            self.hr_request_service.create_agent_run(
                request_id=state["request_id"],
                agent_name=state["selected_agent"],
                input_summary=state["message"][:300],
                output_summary=state.get("response", "")[:500],
                status=state.get("status", "success"),
                error_message=state.get("error_message"),
            )
        self.audit_service.create_log(
            request_id=state["request_id"],
            user_id=state["user_id"],
            message=state["message"],
            classified_intent=state.get("intent"),
            confidence=state.get("confidence"),
            selected_agent=state.get("selected_agent"),
            response_summary=state.get("response", "")[:300],
            status=state.get("status", "success"),
            error_message=state.get("error_message"),
        )

        return state

    @staticmethod
    def _safe_failure_response() -> str:
        """Return a polite failure response without exposing internal errors."""
        return (
            "I’m sorry, I could not complete the request right now. "
            "Please try again shortly or contact HR if the matter is urgent."
        )