from typing import List, Dict, Any, Optional
from app.db.supabase import get_chatbot_supabase_client
import logging
import uuid

logger = logging.getLogger(__name__)

class RetrievedContextRepo:
    """
    Repository for storing retrieved context data.
    Improved schema with better tracking: query, record count, errors, timing.
    Persists verified data retrieved from CRM sources.
    """
    
    def __init__(self):
        self.supabase = get_chatbot_supabase_client()
        self.table = "retrieved_context"
    
    def save_context(
        self, 
        session_id: str,
        admin_id: str,
        source_type: str, 
        query_text: str,
        payload: Dict[str, Any],
        record_count: Optional[int] = None,
        error_message: Optional[str] = None,
        retrieval_time_ms: Optional[int] = None
    ) -> bool:
        """
        Saves retrieved context data to database with improved tracking.
        
        Args:
            session_id: Session UUID
            admin_id: Admin/user ID (will be converted to UUID if needed)
            source_type: One of 'crm', 'none', 'entity_memory', 'pending_action'
            query_text: The original query that triggered this retrieval
            payload: The actual data retrieved (will be stored as JSONB)
            record_count: Number of records retrieved (auto-calculated if None)
            error_message: Error message if retrieval failed (optional)
            retrieval_time_ms: Time taken to retrieve data in milliseconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert admin_id to UUID if needed
            if admin_id == "anonymous" or not admin_id:
                admin_uuid = "00000000-0000-0000-0000-000000000000"
            else:
                try:
                    admin_uuid = str(uuid.UUID(admin_id))
                except ValueError:
                    admin_uuid = "00000000-0000-0000-0000-000000000000"
            
            # Auto-calculate record count if not provided
            if record_count is None:
                if error_message:
                    record_count = 0
                elif isinstance(payload, dict):
                    # Try to get count from payload
                    if "data" in payload and isinstance(payload["data"], list):
                        record_count = len(payload["data"])
                    else:
                        record_count = 1 if payload else 0
                elif isinstance(payload, list):
                    record_count = len(payload)
                else:
                    record_count = 1 if payload else 0
            
            data = {
                "session_id": session_id,
                "admin_id": admin_uuid,
                "source_type": source_type,
                "query_text": query_text,
                "record_count": record_count,
                "payload": payload
            }
            
            if error_message:
                data["error_message"] = error_message
            
            if retrieval_time_ms is not None:
                data["retrieval_time_ms"] = retrieval_time_ms
            
            result = self.supabase.table(self.table).insert(data).execute()
            
            if result.data:
                logger.info(f"Saved retrieved context: {source_type} for session {session_id[:8]}... ({record_count} records)")
                return True
            else:
                logger.error(f"Failed to save retrieved context: {source_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving retrieved context: {e}", exc_info=True)
            return False
    
    def get_context_by_session(
        self, 
        session_id: str, 
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves context data for a session.
        
        Args:
            session_id: Session UUID
            source_type: Optional filter by source type
            
        Returns:
            List of context records
        """
        try:
            query = (
                self.supabase.table(self.table)
                .select("*")
                .eq("session_id", session_id)
            )
            
            if source_type:
                query = query.eq("source_type", source_type)
            
            response = query.order("created_at", desc=True).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error fetching retrieved context: {e}", exc_info=True)
            return []
    
    def get_context_by_admin(
        self,
        admin_id: str,
        source_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves context data for an admin/user.
        
        Args:
            admin_id: Admin/user ID
            source_type: Optional filter by source type
            limit: Maximum number of records to return
            
        Returns:
            List of context records
        """
        try:
            # Convert admin_id to UUID if needed
            try:
                admin_uuid = str(uuid.UUID(admin_id))
            except ValueError:
                admin_uuid = "00000000-0000-0000-0000-000000000000"
            
            query = (
                self.supabase.table(self.table)
                .select("*")
                .eq("admin_id", admin_uuid)
            )
            
            if source_type:
                query = query.eq("source_type", source_type)
            
            response = query.order("created_at", desc=True).limit(limit).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error fetching retrieved context by admin: {e}", exc_info=True)
            return []
