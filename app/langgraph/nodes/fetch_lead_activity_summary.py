"""
LangGraph node for fetching lead activity summary.
Fetches lead and all related activities, then formats using LLM.
"""

from typing import Dict, Any
from app.langgraph.state import AgentState
from app.services.lead_summary_service import LeadSummaryService, LeadNotFoundError
from app.db.retrieved_context_repo import RetrievedContextRepo
from app.core.config import settings
import logging
import asyncio
import time

logger = logging.getLogger(__name__)


async def fetch_lead_activity_summary_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches lead activity summary and formats response using LLM.
    
    This node:
    1. Extracts lead identifier from user message
    2. Calls LeadSummaryService to fetch lead and activities
    3. Formats summary using LLM (formatting only, no hallucination)
    4. Stores structured data in state["retrieved_context"]
    5. Sets state["source_type"] = "lead_summary"
    6. Returns formatted response
    """
    try:
        session_id = state.get("session_id")
        admin_id = state.get("admin_id", "anonymous")
        user_message = state.get("user_message", "")
        
        logger.info(f"[LEAD_SUMMARY] Fetching lead activity summary for query: {user_message[:100]}...")
        
        retrieval_start = time.time()
        
        # Initialize service
        service = LeadSummaryService()
        
        # Check if lead_identifier was set by load_memory_node (contextual resolution)
        lead_identifier = state.get("lead_identifier")
        
        if not lead_identifier:
            # Extract lead identifier from query
            lead_identifier = service._extract_lead_identifier(user_message)
            logger.info(f"[LEAD_SUMMARY] Extracted lead identifier from query: '{lead_identifier}'")
        else:
            logger.info(f"[LEAD_SUMMARY] Using lead identifier from state (contextual resolution): '{lead_identifier}'")
        
        if not lead_identifier:
            logger.warning(f"[LEAD_SUMMARY] Could not extract lead identifier from query: {user_message}")
            return {
                "retrieved_context": [],
                "source_type": "lead_summary",
                "response": "I couldn't identify which lead you're asking about. Please specify the lead name or ID, for example: 'Give me full summary of lead John Doe' or 'Show activity summary for lead ID 132'."
            }
        
        logger.info(f"[LEAD_SUMMARY] Using lead identifier: '{lead_identifier}' for query: '{user_message}'")
        
        # Fetch lead activity summary
        if settings.ENABLE_ASYNC_DB:
            summary_data = await asyncio.to_thread(
                service.get_lead_activity_summary,
                lead_identifier
            )
        else:
            summary_data = service.get_lead_activity_summary(lead_identifier)
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Format summary using LLM (formatting only)
        if settings.ENABLE_ASYNC_DB:
            formatted_response = await asyncio.to_thread(
                service.format_lead_summary_with_llm,
                summary_data
            )
        else:
            formatted_response = service.format_lead_summary_with_llm(summary_data)
        
        total_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Log activity counts (using new structured format)
        lead = summary_data.get("lead", {})
        activity_counts = summary_data.get("activity_counts", {})
        calls_count = activity_counts.get("calls", 0)
        emails_count = activity_counts.get("emails", 0)
        meetings_count = activity_counts.get("meetings", 0)
        notes_count = activity_counts.get("notes", 0)
        
        logger.info(
            f"[LEAD_SUMMARY] Lead {lead.get('id')} (name: {lead.get('name', 'N/A')}) summary generated in {total_time_ms}ms: "
            f"{calls_count} calls, {emails_count} emails, "
            f"{meetings_count} meetings, {notes_count} notes"
        )
        
        # Log formatted response preview
        logger.debug(f"[LEAD_SUMMARY] Formatted response preview (first 200 chars): {formatted_response[:200]}...")
        
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
                            source_type="lead_summary",
                            query_text=user_message,
                            payload={
                                "lead_id": lead.get("id"),
                                "lead_name": lead.get("name"),
                                "calls_count": calls_count,
                                "emails_count": emails_count,
                                "meetings_count": meetings_count,
                                "notes_count": notes_count
                            },
                            record_count=1 + calls_count + emails_count + meetings_count + notes_count,
                            retrieval_time_ms=retrieval_time_ms
                        )
                    else:
                        context_repo.save_context(
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="lead_summary",
                            query_text=user_message,
                            payload={
                                "lead_id": lead.get("id"),
                                "lead_name": lead.get("name"),
                                "calls_count": calls_count,
                                "emails_count": emails_count,
                                "meetings_count": meetings_count,
                                "notes_count": notes_count
                            },
                            record_count=1 + calls_count + emails_count + meetings_count + notes_count,
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
                    source_type="lead_summary",
                    query_text=user_message,
                    payload={
                        "lead_id": lead.get("id"),
                        "lead_name": lead.get("name"),
                        "calls_count": calls_count,
                        "emails_count": emails_count,
                        "meetings_count": meetings_count,
                        "notes_count": notes_count
                    },
                    record_count=1 + calls_count + emails_count + meetings_count + notes_count,
                    retrieval_time_ms=retrieval_time_ms
                )
            else:
                context_repo.save_context(
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="lead_summary",
                    query_text=user_message,
                    payload={
                        "lead_id": lead.get("id"),
                        "lead_name": lead.get("name"),
                        "calls_count": calls_count,
                        "emails_count": emails_count,
                        "meetings_count": meetings_count,
                        "notes_count": notes_count
                    },
                    record_count=1 + calls_count + emails_count + meetings_count + notes_count,
                    retrieval_time_ms=retrieval_time_ms
                )
        
        # Return formatted response (already formatted by LLM in service)
        return {
            "retrieved_context": summary_data,
            "source_type": "lead_summary",
            "response": formatted_response  # Pre-formatted response, bypasses call_llm
        }
        
    except LeadNotFoundError as e:
        logger.warning(f"Lead not found: {e}")
        
        # Persist error context
        try:
            context_repo = RetrievedContextRepo()
            if settings.ENABLE_ASYNC_WRITES:
                async def save_error_context_async():
                    try:
                        if settings.ENABLE_ASYNC_DB:
                            await asyncio.to_thread(
                                context_repo.save_context,
                                session_id=state.get("session_id", "unknown"),
                                admin_id=state.get("admin_id", "anonymous"),
                                source_type="lead_summary",
                                query_text=state.get("user_message", ""),
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=state.get("admin_id", "anonymous"),
                                source_type="lead_summary",
                                query_text=state.get("user_message", ""),
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
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="lead_summary",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="lead_summary",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
        except:
            pass
        
        return {
            "retrieved_context": [],
            "source_type": "lead_summary",
            "response": "Lead not found. Please check the lead name or ID and try again."
        }
        
    except Exception as e:
        logger.error(f"Error fetching lead activity summary: {e}", exc_info=True)
        
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
                                source_type="lead_summary",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="lead_summary",
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
                        source_type="lead_summary",
                        query_text=query,
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="lead_summary",
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
            "source_type": "lead_summary",
            "response": "I encountered an error while fetching the lead activity summary. Please try again."
        }

