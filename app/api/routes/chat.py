from fastapi import APIRouter, HTTPException, Depends, status, Header, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.security import get_admin_token
from app.core.config import settings
from app.services.chat_service import ChatService
from app.db.supabase import get_chatbot_supabase_client
import logging
import uuid

# Define Router
router = APIRouter()
logger = logging.getLogger(__name__)

# Optional rate limiting decorator
# Applied only if ENABLE_RATE_LIMITING=true and slowapi is installed
# Uses the limiter instance from app.state (set in main.py)
# Only applies to /chat endpoints - health and static routes are excluded
def apply_rate_limit(func):
    """
    Apply rate limiting decorator if enabled.
    Only applies to /chat endpoints.
    Health and static routes are excluded.
    Internal calls (without Request) are not rate limited.
    """
    if settings.ENABLE_RATE_LIMITING:
        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address
            from functools import wraps
            
            # Create a decorator that uses the limiter from app.state
            @wraps(func)
            async def rate_limited_wrapper(request: Request, *args, **kwargs):
                """
                Wrapper that applies rate limiting using limiter from app.state.
                If limiter not in app state, skip rate limiting (internal call or not configured).
                """
                # Get limiter from app state (set in main.py)
                if hasattr(request.app.state, 'limiter'):
                    limiter = request.app.state.limiter
                    # Apply rate limit using the limiter from app state
                    # Use the limiter's limit method directly
                    limited_func = limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")(func)
                    return await limited_func(request, *args, **kwargs)
                else:
                    # Limiter not in app state, skip rate limiting
                    return await func(request, *args, **kwargs)
            
            return rate_limited_wrapper
        except ImportError:
            # slowapi not installed, skip rate limiting
            pass
    return func

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """
    Gets existing session or creates a new one if it doesn't exist.
    No authentication required.
    """
    supabase = get_chatbot_supabase_client()
    
    # Try to get existing session (only if it's not a temp session)
    if not session_id.startswith('temp-'):
        try:
            response = (
                supabase.table("admin_sessions")
                .select("session_id, admin_id, status")
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            
            if response.data and response.data["status"] == "active":
                return response.data
        except Exception as e:
            logger.warning(f"Session lookup failed: {e}, creating new session")
    
    # Session doesn't exist or is inactive, create new one
    from app.services.session_service import SessionService
    service = SessionService()
    session_data = service.create_session("anonymous")
    return session_data

@router.post("/message", response_model=ChatResponse)
@apply_rate_limit
async def chat_message(
    request: Request,
    chat_request: ChatRequest
):
    """
    Chat message endpoint with full persistence.
    All data is persisted to database including errors.
    
    Optional rate limiting is applied if ENABLE_RATE_LIMITING=true.
    """
    try:
        # Get or create session (no auth required)
        session_data = get_or_create_session(chat_request.session_id)
        
        # Use the actual session_id from the created/retrieved session
        actual_session_id = session_data["session_id"]
        
        service = ChatService()
        response_text = await service.process_user_message(
            session_id=actual_session_id,
            user_message=chat_request.message,
            session_data=session_data
        )
        
        return ChatResponse(response=response_text, session_id=actual_session_id)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        # Audit log endpoint error
        try:
            from app.db.audit_repo import AuditRepo
            audit = AuditRepo()
            audit.log_action(
                admin_id=session_data.get("admin_id", "unknown") if 'session_data' in locals() else "unknown",
                action="chat_endpoint_error",
                details={"error": str(e), "message": chat_request.message[:100]},
                session_id=session_data.get("session_id") if 'session_data' in locals() else None
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))
