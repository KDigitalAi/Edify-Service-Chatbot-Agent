from typing import List, Dict, Optional, Any
from app.db.supabase import get_chatbot_supabase_client
from app.utils.cache import get_cached, set_cached, cache_key_chat_history
import logging
import uuid

logger = logging.getLogger(__name__)

class MemoryRepo:
    """
    Repository for conversation history.
    Uses chat_history table to load conversation context for LangGraph.
    Note: chat_history stores pairs (user_message + assistant_response),
    so we convert them to the format LangGraph expects (role + content).
    """
    def __init__(self):
        self.supabase = get_chatbot_supabase_client()
        self.table = "chat_history"

    def get_chat_history(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Retrieves recent chat history for a session.
        Converts chat_history pairs to LangGraph format (role + content).
        READ-THROUGH caching: Cache miss → DB query → cache write.
        TTL: 2 minutes for chat history.
        
        Args:
            session_id: Session UUID
            limit: Maximum number of conversation pairs to retrieve
            
        Returns:
            List of messages in format [{"role": "admin", "content": "..."}, ...]
        """
        from app.core.config import settings
        
        # READ-THROUGH: Try cache first (non-breaking if cache unavailable)
        cache_key = cache_key_chat_history(session_id, limit)
        if settings.ENABLE_CACHING:
            cached = get_cached(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for chat history: {session_id[:8]}...")
                return cached
        
        try:
            # Cache miss: Query database
            response = (
                self.supabase.table(self.table)
                .select("user_message, assistant_response, created_at")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            if not response.data:
                # Empty result - don't cache empty results
                return []
            
            # Convert pairs to individual messages in chronological order
            messages = []
            # Reverse to get chronological order (oldest first)
            for pair in reversed(response.data):
                # Add user message
                messages.append({
                    "role": "admin",
                    "content": pair["user_message"]
                })
                # Add assistant response
                messages.append({
                    "role": "assistant",
                    "content": pair["assistant_response"]
                })
            
            # READ-THROUGH: Cache successful read result (TTL: 2 minutes = 120 seconds)
            # Only cache if we got messages (successful read)
            if settings.ENABLE_CACHING and messages:
                set_cached(cache_key, messages, ttl=120)
            
            logger.debug(f"Loaded {len(messages)} messages from chat_history for session {session_id[:8]}...")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}", exc_info=True)
            # Don't cache errors - return empty list
            return []

    def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        source_type: Optional[str] = None
    ) -> bool:
        """
        DEPRECATED: This method is kept for backward compatibility but does nothing.
        Messages are now saved as pairs in chat_history table via ChatService.
        
        This method exists because some code still calls it, but chat_history
        is saved in ChatService.process_user_message() after the full conversation pair.
        
        Args:
            session_id: Session UUID
            role: Message role ('admin', 'assistant', 'system')
            content: Message content
            source_type: Optional source type (not used here)
            
        Returns:
            True (always succeeds, but doesn't actually save)
        """
        # Chat history is now saved as pairs in ChatService
        # This method is kept for backward compatibility
        logger.debug(f"save_message called for {role} message (deprecated - using chat_history pairs)")
        return True
    
    def save_entity_memory(
        self,
        session_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        entity_name: Optional[str] = None
    ) -> bool:
        """
        Saves entity memory for conversational continuity.
        Stores the last entity that was created/updated/deleted in a session.
        
        Args:
            session_id: Session UUID
            entity_type: Type of entity (e.g., 'lead', 'campaign', 'task')
            entity_id: ID of the entity
            action: Action performed ('create', 'update', 'delete', 'read')
            entity_name: Optional name of the entity
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use chat_history table's metadata or create a simple JSONB field
            # For now, we'll store in a separate table structure via JSONB in chat_history
            # Or we can use retrieved_context table with a special source_type
            
            # Actually, let's use a simpler approach: store in retrieved_context with source_type='entity_memory'
            from app.db.retrieved_context_repo import RetrievedContextRepo
            context_repo = RetrievedContextRepo()
            
            payload = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action
            }
            if entity_name:
                payload["entity_name"] = entity_name
            
            # Store as retrieved_context with special source_type
            # Note: We'll need to update retrieved_context_repo to accept 'entity_memory' as source_type
            success = context_repo.save_context(
                session_id=session_id,
                admin_id="system",  # System-generated memory
                source_type="entity_memory",  # Special source type for entity memory
                query_text=f"{action}_{entity_type}_{entity_id}",
                payload=payload,
                record_count=1
            )
            
            if success:
                logger.info(f"Saved entity memory: {entity_type} {entity_id} ({action}) for session {session_id[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving entity memory: {e}", exc_info=True)
            return False
    
    def get_entity_memory(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent entity memory for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Dictionary with entity_type, entity_id, action, entity_name if found, None otherwise
        """
        try:
            from app.db.retrieved_context_repo import RetrievedContextRepo
            context_repo = RetrievedContextRepo()
            
            # Get most recent entity memory for this session
            contexts = context_repo.get_context_by_session(session_id, source_type="entity_memory")
            
            if not contexts or len(contexts) == 0:
                return None
            
            # Get the most recent one (first in list since it's ordered DESC)
            latest = contexts[0]
            payload = latest.get("payload", {})
            
            if not isinstance(payload, dict):
                return None
            
            entity_memory = {
                "entity_type": payload.get("entity_type"),
                "entity_id": payload.get("entity_id"),
                "action": payload.get("action"),
                "entity_name": payload.get("entity_name")
            }
            
            # Validate required fields
            if not entity_memory.get("entity_type") or not entity_memory.get("entity_id"):
                return None
            
            logger.debug(f"Loaded entity memory: {entity_memory['entity_type']} {entity_memory['entity_id']} for session {session_id[:8]}...")
            return entity_memory
            
        except Exception as e:
            logger.error(f"Error loading entity memory: {e}", exc_info=True)
            return None
    
    def save_pending_action(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> bool:
        """
        Saves pending action that requires confirmation.
        Used for destructive actions (delete, etc.) that need user confirmation.
        
        Args:
            session_id: Session UUID
            tool_name: Name of the tool/action (e.g., 'delete_lead')
            arguments: Arguments for the action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from app.db.retrieved_context_repo import RetrievedContextRepo
            context_repo = RetrievedContextRepo()
            
            # Extract entity_type and entity_id from tool_name and arguments
            entity_type = tool_name.replace("delete_", "").replace("update_", "").replace("create_", "")
            entity_id_param = f"{entity_type}_id"
            entity_id = arguments.get(entity_id_param)
            
            payload = {
                "tool_name": tool_name,
                "arguments": arguments,
                "entity_type": entity_type
            }
            if entity_id:
                payload["entity_id"] = str(entity_id)
            
            success = context_repo.save_context(
                session_id=session_id,
                admin_id="system",
                source_type="pending_action",
                query_text=f"pending_{tool_name}",
                payload=payload,
                record_count=1
            )
            
            if success:
                logger.info(f"Saved pending action: {tool_name} for session {session_id[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving pending action: {e}", exc_info=True)
            return False
    
    def get_pending_action(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent pending action for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Dictionary with tool_name, arguments, entity_type, entity_id if found, None otherwise
        """
        try:
            from app.db.retrieved_context_repo import RetrievedContextRepo
            context_repo = RetrievedContextRepo()
            
            # Get most recent pending action for this session
            contexts = context_repo.get_context_by_session(session_id, source_type="pending_action")
            
            if not contexts or len(contexts) == 0:
                return None
            
            # Get the most recent one (first in list since it's ordered DESC)
            latest = contexts[0]
            payload = latest.get("payload", {})
            
            if not isinstance(payload, dict):
                return None
            
            pending_action = {
                "tool_name": payload.get("tool_name"),
                "arguments": payload.get("arguments", {}),
                "entity_type": payload.get("entity_type"),
                "entity_id": payload.get("entity_id")
            }
            
            # Validate required fields
            if not pending_action.get("tool_name") or not pending_action.get("arguments"):
                return None
            
            logger.debug(f"Loaded pending action: {pending_action['tool_name']} for session {session_id[:8]}...")
            return pending_action
            
        except Exception as e:
            logger.error(f"Error loading pending action: {e}", exc_info=True)
            return None
    
    def clear_pending_action(self, session_id: str) -> bool:
        """
        Clears pending action for a session by deleting the most recent pending_action record.
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get pending action first to get the record ID
            from app.db.retrieved_context_repo import RetrievedContextRepo
            context_repo = RetrievedContextRepo()
            
            contexts = context_repo.get_context_by_session(session_id, source_type="pending_action")
            if not contexts or len(contexts) == 0:
                return True  # Nothing to clear
            
            # Get the most recent one (first in list)
            latest = contexts[0]
            record_id = latest.get("id")
            
            if not record_id:
                return True  # No ID to delete
            
            # Delete the specific record by ID
            response = (
                self.supabase.table("retrieved_context")
                .delete()
                .eq("id", record_id)
                .execute()
            )
            
            logger.info(f"Cleared pending action (ID: {record_id}) for session {session_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing pending action: {e}", exc_info=True)
            return False