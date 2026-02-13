from typing import List, Dict, Any, Optional, TypedDict
import operator

class AgentState(TypedDict):
    """
    State model for SalesBot CRM Agentic AI.
    """
    session_id: str
    admin_id: str
    user_message: str
    conversation_history: List[Dict[str, str]]
    retrieved_context: Optional[Any]
    source_type: Optional[str]
    response: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]  # LLM function calls
    action_results: Optional[List[Dict[str, Any]]]  # Results from executed actions
    requires_confirmation: Optional[bool]  # For destructive actions
    pending_action: Optional[Dict[str, Any]]  # Action waiting for confirmation
