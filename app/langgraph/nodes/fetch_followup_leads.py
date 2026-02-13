"""
LangGraph node for fetching leads requiring follow-up.
Bypasses LLM and returns formatted response directly.
"""

from typing import Dict, Any
from app.langgraph.state import AgentState
from app.services.followup_service import FollowUpService
from app.db.retrieved_context_repo import RetrievedContextRepo
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


def format_followup_response(leads: list) -> str:
    """
    Format leads list into human-readable response.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Formatted string response
    """
    if not leads or len(leads) == 0:
        return "No leads require follow-up today."
    
    response_lines = [f"Here are the leads requiring follow-up today:\n"]
    
    for idx, lead in enumerate(leads, start=1):
        name = lead.get("name", "N/A")
        phone = lead.get("phone", "N/A")
        email = lead.get("email", "N/A")
        status = lead.get("lead_status", "N/A")
        follow_up = lead.get("next_follow_up", "N/A")
        owner = lead.get("lead_owner", "N/A")
        
        # Format follow-up date (remove time if present)
        if follow_up and follow_up != "N/A":
            try:
                # Extract date part if datetime string
                if "T" in str(follow_up):
                    follow_up = str(follow_up).split("T")[0]
            except:
                pass
        
        response_lines.append(f"{idx}. {name}")
        response_lines.append(f"   Phone: {phone}")
        if email and email != "N/A":
            response_lines.append(f"   Email: {email}")
        response_lines.append(f"   Status: {status}")
        response_lines.append(f"   Follow-Up: {follow_up}")
        if owner and owner != "N/A":
            response_lines.append(f"   Owner: {owner}")
        response_lines.append("")  # Empty line between leads
    
    return "\n".join(response_lines)


async def fetch_followup_leads_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches leads requiring follow-up and formats response.
    Bypasses LLM - returns formatted response directly.
    
    This node:
    1. Calls FollowUpService to get leads
    2. Formats the response
    3. Sets response in state (bypassing LLM)
    4. Persists context to database
    """
    try:
        session_id = state.get("session_id")
        admin_id = state.get("admin_id", "anonymous")
        user_message = state.get("user_message", "")
        
        logger.info(f"Fetching leads requiring follow-up for query: {user_message[:50]}...")
        
        import time
        retrieval_start = time.time()
        
        # Get follow-up leads
        service = FollowUpService()
        
        # Execute in thread pool if async enabled, otherwise synchronous
        if settings.ENABLE_ASYNC_DB:
            leads = await asyncio.to_thread(service.get_leads_requiring_followup)
        else:
            leads = service.get_leads_requiring_followup()
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Format response (bypass LLM)
        formatted_response = format_followup_response(leads)
        
        logger.info(f"Found {len(leads)} leads requiring follow-up in {retrieval_time_ms}ms")
        
        # Persist retrieved context to database
        context_repo = RetrievedContextRepo()
        
        if settings.ENABLE_ASYNC_WRITES:
            # Save context in background task (non-blocking, fire-and-forget)
            async def save_context_async():
                """Save context in background without blocking main request."""
                try:
                    if settings.ENABLE_ASYNC_DB:
                        await asyncio.to_thread(
                            context_repo.save_context,
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="followup",
                            query_text=user_message,
                            payload={"data": leads, "count": len(leads)},
                            record_count=len(leads),
                            retrieval_time_ms=retrieval_time_ms
                        )
                    else:
                        context_repo.save_context(
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="followup",
                            query_text=user_message,
                            payload={"data": leads, "count": len(leads)},
                            record_count=len(leads),
                            retrieval_time_ms=retrieval_time_ms
                        )
                except Exception as save_error:
                    logger.error(f"Background context save failed: {save_error}", exc_info=True)
            
            # Create background task (fire-and-forget, no await)
            asyncio.create_task(save_context_async())
            logger.debug("Context save scheduled in background task")
        else:
            # Existing sync behavior (blocking)
            if settings.ENABLE_ASYNC_DB:
                await asyncio.to_thread(
                    context_repo.save_context,
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="followup",
                    query_text=user_message,
                    payload={"data": leads, "count": len(leads)},
                    record_count=len(leads),
                    retrieval_time_ms=retrieval_time_ms
                )
            else:
                context_repo.save_context(
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="followup",
                    query_text=user_message,
                    payload={"data": leads, "count": len(leads)},
                    record_count=len(leads),
                    retrieval_time_ms=retrieval_time_ms
                )
        
        # Return formatted response directly (bypass LLM)
        return {
            "retrieved_context": leads if leads else [],
            "source_type": "followup",
            "response": formatted_response  # Direct response, bypasses LLM
        }
        
    except Exception as e:
        logger.error(f"Error fetching follow-up leads: {e}", exc_info=True)
        
        # Persist error context
        try:
            context_repo = RetrievedContextRepo()
            admin_id = state.get("admin_id", "anonymous")
            query = state.get("user_message", "")
            
            if settings.ENABLE_ASYNC_WRITES:
                async def save_error_context_async():
                    try:
                        if settings.ENABLE_ASYNC_DB:
                            await asyncio.to_thread(
                                context_repo.save_context,
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="followup",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="followup",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"Background error context save failed: {save_error}", exc_info=True)
                
                asyncio.create_task(save_error_context_async())
            else:
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="followup",
                        query_text=query,
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="followup",
                        query_text=query,
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
        except:
            pass
        
        # Return error response
        return {
            "retrieved_context": [],
            "source_type": "followup",
            "response": "I encountered an error while fetching leads requiring follow-up. Please try again."
        }

