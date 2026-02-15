from typing import Dict, Any, List, Optional, Tuple
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
    
    # CONTEXTUAL REFERENCE PATTERNS: Detect references to previously displayed items
    contextual_patterns = [
        r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+(one|lead|item|record|entry)\b',
        r'\b(last)\s+(one|lead|item|record|entry)\b',
        r'\b(that|this)\s+(lead|one|record|item)\b',
        r'\b(it|them)\b',  # Simple pronouns (context-dependent)
        r'\btell\s+me\s+about\s+(the\s+)?(first|second|third|fourth|fifth|last|that|this)\b',
        r'\bshow\s+(me\s+)?(details?|info|information)\s+(of|for|about)\s+(the\s+)?(first|second|third|fourth|fifth|last|that|this)\b',
        r'\bexplain\s+(the\s+)?(first|second|third|fourth|fifth|last|that|this)\b'
    ]
    
    has_contextual = any(re.search(pattern, query_lower) for pattern in contextual_patterns)
    
    if has_follow_up or has_contextual:
        if has_contextual:
            logger.debug(f"Loading history for contextual reference query: {query[:50]}...")
        else:
            logger.debug(f"Loading history for follow-up/context-dependent query: {query[:50]}...")
        return True
    
    # Default: Load history for ambiguous cases (better safe than sorry)
    # But log that we're loading it
    logger.debug(f"Loading history (default for query): {query[:50]}...")
    return True


def _detect_contextual_reference(query: str) -> Optional[Tuple[str, int]]:
    """
    Detects if query contains a contextual reference (first, second, last, etc.).
    
    Args:
        query: User's query
        
    Returns:
        Tuple of (reference_type, index) if detected, None otherwise.
        reference_type: "ordinal" (first, second, etc.) or "pronoun" (that, this, it)
        index: 0-based index (first=0, second=1, last=-1)
    """
    query_lower = query.lower().strip()
    
    # Ordinal patterns: first, second, third, etc.
    ordinal_map = {
        "first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
        "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9
    }
    
    for ordinal, index in ordinal_map.items():
        pattern = rf'\b{ordinal}\s+(one|lead|item|record|entry)\b'
        if re.search(pattern, query_lower):
            logger.info(f"[CONTEXTUAL] Detected ordinal reference: {ordinal} (index {index})")
            return ("ordinal", index)
    
    # "Last" pattern
    if re.search(r'\blast\s+(one|lead|item|record|entry)\b', query_lower):
        logger.info(f"[CONTEXTUAL] Detected 'last' reference (index -1)")
        return ("ordinal", -1)
    
    # Pronoun patterns: that, this, it
    if re.search(r'\b(that|this)\s+(lead|one|record|item)\b', query_lower):
        logger.info(f"[CONTEXTUAL] Detected pronoun reference: that/this")
        return ("pronoun", 0)  # Default to first item
    
    # Simple "it" or "them" (context-dependent)
    if re.search(r'\b(it|them)\b', query_lower) and any(word in query_lower for word in ["tell", "show", "explain", "about", "details"]):
        logger.info(f"[CONTEXTUAL] Detected simple pronoun reference: it/them")
        return ("pronoun", 0)  # Default to first item
    
    return None


def _extract_lead_list_from_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Extracts a list of leads from assistant response text.
    Handles numbered list format: "1. Name", "2. Name", etc.
    
    Args:
        response_text: Assistant's previous response text
        
    Returns:
        List of lead dictionaries with 'name' and optionally 'id'
    """
    leads = []
    
    if not response_text:
        return leads
    
    # Pattern to match numbered list items: "1. Name" or "1) Name"
    # Also handles formats like "1. Name\n   Phone: ..." (multi-line entries)
    pattern = r'^(\d+)\.\s+([^\n]+)'
    
    lines = response_text.split('\n')
    current_lead = None
    
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            # Save previous lead if exists
            if current_lead:
                leads.append(current_lead)
            
            # Start new lead
            index = int(match.group(1))
            name_part = match.group(2).strip()
            
            # Extract name (might have additional info, take first part)
            # Handle cases like "1. John Doe" or "1. John Doe - Status: Active"
            name = name_part.split(' - ')[0].split(' (')[0].strip()
            
            # Try to extract ID if present (e.g., "1. John Doe (ID: 123)")
            lead_id = None
            id_match = re.search(r'\(ID:\s*(\d+)\)', name_part)
            if id_match:
                lead_id = int(id_match.group(1))
            
            current_lead = {
                'name': name,
                'index': index - 1,  # Convert to 0-based
                'id': lead_id
            }
        elif current_lead and line.strip():
            # Check if line contains ID information
            id_match = re.search(r'ID[:\s]+(\d+)', line, re.IGNORECASE)
            if id_match and not current_lead.get('id'):
                current_lead['id'] = int(id_match.group(1))
    
    # Add last lead if exists
    if current_lead:
        leads.append(current_lead)
    
    logger.debug(f"[CONTEXTUAL] Extracted {len(leads)} leads from previous response")
    return leads


def _resolve_contextual_reference(
    query: str,
    history: List[Dict[str, str]]
) -> Optional[str]:
    """
    Resolves a contextual reference to a lead identifier.
    
    Args:
        query: User's query with contextual reference
        history: Conversation history (list of messages with 'role' and 'content')
        
    Returns:
        Lead identifier (name or ID as string) if resolved, None otherwise
    """
    # Detect contextual reference
    contextual_info = _detect_contextual_reference(query)
    if not contextual_info:
        return None
    
    ref_type, index = contextual_info
    
    # Find last assistant response
    last_assistant_response = None
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            last_assistant_response = msg.get("content", "")
            break
    
    if not last_assistant_response:
        logger.warning("[CONTEXTUAL] No previous assistant response found")
        return None
    
    logger.info(f"[CONTEXTUAL] Found previous assistant response (length: {len(last_assistant_response)} chars)")
    
    # Extract lead list from response
    leads = _extract_lead_list_from_response(last_assistant_response)
    
    if not leads:
        logger.warning("[CONTEXTUAL] Could not extract lead list from previous response")
        return None
    
    logger.info(f"[CONTEXTUAL] Extracted {len(leads)} leads from previous response")
    
    # Resolve index
    if index == -1:  # "last"
        resolved_index = len(leads) - 1
    elif index >= len(leads):
        logger.warning(f"[CONTEXTUAL] Index {index} out of range (list has {len(leads)} items)")
        return None
    else:
        resolved_index = index
    
    if resolved_index < 0 or resolved_index >= len(leads):
        logger.warning(f"[CONTEXTUAL] Resolved index {resolved_index} out of range")
        return None
    
    selected_lead = leads[resolved_index]
    
    # Prefer ID over name if available
    if selected_lead.get('id'):
        identifier = str(selected_lead['id'])
        logger.info(f"[CONTEXTUAL] Resolved to lead ID: {identifier} (name: {selected_lead.get('name')})")
    else:
        identifier = selected_lead.get('name')
        logger.info(f"[CONTEXTUAL] Resolved to lead name: {identifier}")
    
    return identifier

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
        from app.langgraph.nodes.decide_source import is_greeting, get_greeting_response, decide_source_node
        
        user_message = state.get("user_message", "")
        
        # Handle greetings - set response and source_type
        if is_greeting(user_message):
            logger.info("Greeting detected in load_memory, setting response")
            return {
                "source_type": "none",
                "response": get_greeting_response(),
                "conversation_history": []
            }
        
        # CRITICAL: Detect intent and set source_type BEFORE loading history
        # This ensures proper routing to send_email, followup, email_draft, etc.
        intent_result = decide_source_node(state)
        source_type = intent_result.get("source_type", "crm")
        
        # If decide_source_node already set a response (e.g., greeting), return it
        if intent_result.get("response"):
            return {
                **intent_result,
                "conversation_history": []
            }
        
        logger.info(f"[LOAD_MEMORY] Intent detected: {source_type} for query: '{user_message[:50]}...'")
        
        # Check if history is needed
        if not _needs_history(user_message):
            logger.info(f"Skipping history load for query: {user_message[:50]}...")
            return {
                "conversation_history": [],
                "source_type": source_type  # Ensure source_type is set even when skipping history
            }
        
        # History is needed - load it
        session_id = state["session_id"]
        repo = MemoryRepo()
        history = repo.get_chat_history(session_id, limit=10)
        
        # CONTEXTUAL RESOLUTION: Check if query contains contextual reference
        # If so, resolve it to a lead identifier
        contextual_identifier = _resolve_contextual_reference(user_message, history)
        
        if contextual_identifier:
            logger.info(f"[CONTEXTUAL] Resolved contextual reference to lead identifier: '{contextual_identifier}'")
            
            # Check if this is an email sending request
            # If so, keep source_type as "send_email" but set lead_identifier
            if source_type == "send_email":
                logger.info(f"[CONTEXTUAL] Contextual reference in send_email query - setting lead_identifier: '{contextual_identifier}'")
                # Don't override source_type, just set lead_identifier
                # The send_email_node will use this identifier
            else:
                # Default: route to lead_summary for contextual references
                logger.info(f"[CONTEXTUAL] Overriding source_type from '{source_type}' to 'lead_summary'")
                source_type = "lead_summary"
                # Update user_message to be clearer for lead summary
                user_message = f"Give me full summary of lead {contextual_identifier}"
            
            # Return with contextual identifier set
            return {
                "conversation_history": history,
                "source_type": source_type,
                "lead_identifier": contextual_identifier,  # Set identifier for routing
                "user_message": user_message  # Updated query if needed
            }
        else:
            # Contextual reference detected but couldn't be resolved
            # Check if query contains contextual reference pattern
            contextual_info = _detect_contextual_reference(user_message)
            if contextual_info:
                logger.warning(f"[CONTEXTUAL] Contextual reference detected but could not be resolved")
                # Return error response for contextual reference that couldn't be resolved
                return {
                    "conversation_history": history,
                    "source_type": "none",
                    "response": "I couldn't determine which lead you're referring to. Please specify the lead name or ID, for example: 'Tell me about lead John Doe' or 'Show details of lead 132'."
                }
        
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
            "source_type": source_type,  # CRITICAL: Set source_type for proper routing
            **entity_memory,  # Inject entity memory into state
            **pending_action_memory  # Inject pending action memory into state
        }
        
    except Exception as e:
        logger.error(f"Error loading memory: {e}")
        # Non-critical, can proceed with empty history
        return {"conversation_history": []}
