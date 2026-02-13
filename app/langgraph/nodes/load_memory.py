from typing import Dict, Any
from app.langgraph.state import AgentState
from app.db.memory_repo import MemoryRepo
import logging
import re

logger = logging.getLogger(__name__)

def _needs_history(query: str) -> bool:
    """
    Determines if conversation history is needed for this query.
    
    Returns True if history is needed (follow-up questions, context-dependent queries).
    Returns False if history can be skipped (greetings, list-only queries).
    
    Args:
        query: User's message/query
        
    Returns:
        True if history should be loaded, False otherwise
    """
    query_lower = query.lower().strip()
    
    # Skip history for greetings
    greeting_patterns = [
        r'^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|day))',
        r'^(hi|hello|hey)\s*[!.]*$',
        r'^how\s+are\s+you',
        r'^what\'?s\s+up',
        r'^thanks?',
        r'^thank\s+you',
        r'^bye',
        r'^goodbye',
        r'^see\s+you'
    ]
    
    for pattern in greeting_patterns:
        if re.search(pattern, query_lower):
            logger.debug(f"Skipping history for greeting: {query[:50]}...")
            return False
    
    # Skip history for list-only queries (simple data retrieval)
    list_query_patterns = [
        r'^(show|list|get|give|display|fetch)\s+(me\s+)?(all\s+)?(the\s+)?',
        r'^(show|list|get|give|display|fetch)\s+(all\s+)?(the\s+)?',
        r'^all\s+(the\s+)?(leads?|trainers?|campaigns?|tasks?|learners?|courses?|candidates?|jobs?|companies?|interviews?)',
        r'^(leads?|trainers?|campaigns?|tasks?|learners?|courses?|candidates?|jobs?|companies?|interviews?)\s+(list|details?|info|information)',
        r'^what\s+(are|is)\s+(all\s+)?(the\s+)?',
    ]
    
    # Check if it's a simple list query (no context dependency)
    is_simple_list = any(re.search(pattern, query_lower) for pattern in list_query_patterns)
    
    # If it's a simple list query and doesn't contain follow-up indicators, skip history
    if is_simple_list:
        # Check for follow-up indicators that would require history
        follow_up_indicators = [
            r'\b(that|those|them|it|this|these)\b',
            r'\b(more|also|and|next|previous|above|below|before|after)\b',
            r'\b(what\s+about|tell\s+me\s+more|show\s+me\s+more|give\s+me\s+more)',
            r'\b(same|similar|other|another|different)\b',
            r'\b(related|associated|connected)\b'
        ]
        
        has_follow_up = any(re.search(pattern, query_lower) for pattern in follow_up_indicators)
        
        if not has_follow_up:
            logger.debug(f"Skipping history for list-only query: {query[:50]}...")
            return False
    
    # Load history for follow-up questions and context-dependent queries
    follow_up_patterns = [
        r'\b(what\s+about|tell\s+me\s+more|show\s+me\s+more|give\s+me\s+more|and\s+what\s+about)\b',
        r'\b(what\s+(else|about|is|are)|how\s+(about|is|are))\b',
        r'\b(also|too|as\s+well|additionally|furthermore)\b',
        r'\b(more|next|previous|another|other|different)\b',
        r'\b(that|those|them|it|this|these)\b',
        r'\b(same|similar|related|associated|connected)\b',
        r'^(and|or|but|then|so)\s+',
        r'^(what|which|who|where|when|how)\s+(about|is|are|was|were)\s+(that|those|them|it|this|these)',
        r'\b(explain|describe|elaborate|expand)\s+(on\s+)?(that|those|them|it|this|these)',
        r'\b(continue|go\s+on|keep\s+going)\b'
    ]
    
    has_follow_up = any(re.search(pattern, query_lower) for pattern in follow_up_patterns)
    
    if has_follow_up:
        logger.debug(f"Loading history for follow-up/context-dependent query: {query[:50]}...")
        return True
    
    # Default: Load history for ambiguous cases (better safe than sorry)
    # But log that we're loading it
    logger.debug(f"Loading history (default for query): {query[:50]}...")
    return True

def load_memory_node(state: AgentState) -> Dict[str, Any]:
    """
    Loads conversation history into state.
    Optimized: Only loads history when needed (follow-up questions, context-dependent queries).
    Skips history for greetings and simple list-only queries.
    
    Also extracts entity memory from conversation history (last created/updated entity IDs).
    Handles greeting detection and sets appropriate state.
    
    Output format: returns {"conversation_history": [...], "entity_memory": {...}}
    """
    try:
        from app.langgraph.nodes.decide_source import is_greeting, get_greeting_response
        
        user_message = state.get("user_message", "")
        
        # Handle greetings - set response and source_type
        if is_greeting(user_message):
            logger.info("Greeting detected in load_memory, setting response")
            return {
                "source_type": "none",
                "response": get_greeting_response(),
                "conversation_history": []
            }
        
        # Check if history is needed
        if not _needs_history(user_message):
            logger.info(f"Skipping history load for query: {user_message[:50]}...")
            return {"conversation_history": []}
        
        # History is needed - load it
        session_id = state["session_id"]
        repo = MemoryRepo()
        history = repo.get_chat_history(session_id, limit=10)
        
        # ENTITY MEMORY: Load persisted entity memory from database
        # This provides cross-request continuity for ALL CRM entities
        entity_memory = {}
        try:
            entity_mem = repo.get_entity_memory(session_id)
            if entity_mem:
                entity_type = entity_mem.get("entity_type")
                entity_id = entity_mem.get("entity_id")
                entity_name = entity_mem.get("entity_name")
                
                if entity_type and entity_id:
                    # Set generic last entity fields
                    entity_memory["last_entity_type"] = entity_type
                    entity_memory["last_entity_id"] = entity_id
                    
                    # Set entity-specific fields for backward compatibility
                    entity_memory[f"last_{entity_type}_id"] = entity_id
                    
                    if entity_name:
                        entity_memory["last_entity_name"] = entity_name
                        entity_memory[f"last_{entity_type}_name"] = entity_name
                    
                    logger.info(f"Restored entity memory: {entity_type} {entity_id} for session {session_id[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to load entity memory: {e}")
        
        # PENDING ACTION: Load persisted pending action from database
        # This provides cross-request continuity for confirmation flows
        pending_action_memory = {}
        try:
            pending_action = repo.get_pending_action(session_id)
            if pending_action:
                pending_action_memory["pending_action"] = {
                    "tool_name": pending_action.get("tool_name"),
                    "arguments": pending_action.get("arguments", {})
                }
                pending_action_memory["requires_confirmation"] = True
                logger.info(f"Restored pending action: {pending_action.get('tool_name')} for session {session_id[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to load pending action: {e}")
        
        logger.debug(f"Loaded {len(history)} history messages for session {session_id[:8]}...")
        if entity_memory:
            logger.debug(f"Entity memory restored: {list(entity_memory.keys())}")
        
        return {
            "conversation_history": history,
            **entity_memory,  # Inject entity memory into state
            **pending_action_memory  # Inject pending action memory into state
        }
        
    except Exception as e:
        logger.error(f"Error loading memory: {e}")
        # Non-critical, can proceed with empty history
        return {"conversation_history": []}
