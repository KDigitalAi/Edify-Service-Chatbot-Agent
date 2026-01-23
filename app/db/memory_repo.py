from typing import List, Dict, Optional
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
