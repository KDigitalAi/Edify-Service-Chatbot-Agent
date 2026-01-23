from typing import Dict, Any
from app.langgraph.state import AgentState
from app.db.retrieved_context_repo import RetrievedContextRepo
from app.db.audit_repo import AuditRepo
from app.core.config import settings
import logging
import threading

logger = logging.getLogger(__name__)

def check_context_node(state: AgentState) -> Dict[str, Any]:
    """
    Checks if retrieved_context has data.
    Handles greeting responses (source_type="none").
    Persists no-data-found events to database.
    """
    context = state.get("retrieved_context")
    source = state.get("source_type", "general")
    session_id = state.get("session_id")
    admin_id = state.get("admin_id", "anonymous")
    
    # If response already set (e.g., greeting), skip data checks
    if state.get("response"):
        # Don't store greetings in retrieved_context - they're not data retrievals
        # Greetings are handled by audit_logs if needed
        return {}
    
    # If general or none, we don't need context
    if source == "general" or source == "none":
        return {}
        
    if not context or (isinstance(context, list) and len(context) == 0):
        # No data found - this should be rare for valid CRM/LMS/RMS/RAG intents
        # Log this as it indicates a potential issue with data retrieval
        query = state.get("user_message", "")
        logger.warning(f"No data found for {source} query: {query[:100]}")
        
        # Persist this event for analysis
        # Optional: Move context saving off main request path using background tasks
        try:
            context_repo = RetrievedContextRepo()
            
            if settings.ENABLE_ASYNC_WRITES:
                # Save context in background thread (non-blocking, fire-and-forget)
                # Since this is a sync function, use threading instead of asyncio
                def save_no_data_context_thread():
                    """Save no-data-found context in background thread without blocking main request."""
                    try:
                        context_repo.save_context(
                            session_id=session_id or "unknown",
                            admin_id=admin_id,
                            source_type=source or "none",
                            query_text=query,
                            payload={"status": "no_data_found"},
                            record_count=0,
                            error_message="No data found"
                        )
                    except Exception as save_error:
                        logger.error(f"Background no-data context save failed: {save_error}", exc_info=True)
                
                # Create background thread (fire-and-forget, daemon thread)
                thread = threading.Thread(target=save_no_data_context_thread, daemon=True)
                thread.start()
                logger.debug("No-data context save scheduled in background thread")
            else:
                # Existing sync behavior (blocking)
                context_repo.save_context(
                    session_id=session_id or "unknown",
                    admin_id=admin_id,
                    source_type=source or "none",
                    query_text=query,
                    payload={"status": "no_data_found"},  # Only store status, query is in query_text column
                    record_count=0,
                    error_message="No data found"
                )
            
            # Audit log no data found (always sync - audit logs are critical)
            audit = AuditRepo()
            audit.log_action(
                admin_id=admin_id,
                action="no_data_found",
                details={
                    "source_type": source,
                    "query": query
                },
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"Error persisting no-data-found event: {e}")
        
        # Return user-friendly message
        # Note: With improved intent detection, this should rarely occur for valid CRM queries
        return {"response": "I couldn't find any data matching your request. Please try rephrasing or check if the data exists in the system.", "next_step": "end"}
        
    # Data found, proceed to LLM
    return {}
