"""
LangGraph node for generating email drafts.
Fetches lead context and generates professional email drafts.
"""

from typing import Dict, Any
from app.langgraph.state import AgentState
from app.services.email_draft_service import EmailDraftService
from app.services.lead_summary_service import LeadNotFoundError
from app.db.retrieved_context_repo import RetrievedContextRepo
from app.core.config import settings
import logging
import asyncio
import time
import json

logger = logging.getLogger(__name__)


def format_email_draft_response(draft_data: Dict[str, Any]) -> str:
    """
    Format email draft into human-readable response.
    
    Args:
        draft_data: Dictionary from EmailDraftService.generate_email_draft()
        
    Returns:
        Formatted string response
    """
    template_type = draft_data.get("template_used", "email")
    subject = draft_data.get("subject", "Email Draft")
    body = draft_data.get("body", "")
    lead_name = draft_data.get("lead_name", "Lead")
    
    # Format template type for display
    template_display = template_type.replace("_", " ").title()
    
    response_lines = [
        f"Email Draft Generated ({template_display} Template)",
        "",
        f"To: {lead_name}",
        f"Subject: {subject}",
        "",
        "Body:",
        body,
        "",
        f"Note: This is a draft. Review and edit before sending."
    ]
    
    return "\n".join(response_lines)


async def generate_email_draft_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates email draft for a lead based on context.
    
    This node:
    1. Extracts lead identifier from user message
    2. Fetches lead information and latest interaction
    3. Determines appropriate email template type
    4. Generates email draft using LLM
    5. Returns formatted response
    """
    try:
        session_id = state.get("session_id")
        admin_id = state.get("admin_id", "anonymous")
        user_message = state.get("user_message", "")
        
        logger.info(f"[EMAIL_DRAFT] Generating email draft for query: {user_message[:100]}...")
        
        retrieval_start = time.time()
        
        # Initialize service
        service = EmailDraftService()
        
        # Extract lead identifier from query
        lead_identifier = service.lead_summary_service._extract_lead_identifier(user_message)
        
        if not lead_identifier:
            logger.warning(f"[EMAIL_DRAFT] Could not extract lead identifier from query: {user_message}")
            return {
                "retrieved_context": [],
                "source_type": "email_draft",
                "response": "I couldn't identify which lead you're asking about. Please specify the lead name or ID, for example: 'Draft follow-up email for lead John Doe' or 'Write email for lead ID 132'."
            }
        
        logger.info(f"[EMAIL_DRAFT] Extracted lead identifier: '{lead_identifier}' from query: '{user_message}'")
        
        # Generate email draft
        if settings.ENABLE_ASYNC_DB:
            draft_data = await asyncio.to_thread(
                service.generate_email_draft,
                lead_identifier
            )
        else:
            draft_data = service.generate_email_draft(lead_identifier)
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Format response
        formatted_response = format_email_draft_response(draft_data)
        
        logger.info(
            f"[EMAIL_DRAFT] Email draft generated in {retrieval_time_ms}ms for lead {draft_data.get('lead_id')} "
            f"(template: {draft_data.get('template_used')})"
        )
        
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
                            source_type="email_draft",
                            query_text=user_message,
                            payload={
                                "lead_id": draft_data.get("lead_id"),
                                "lead_name": draft_data.get("lead_name"),
                                "template_type": draft_data.get("template_used"),
                                "subject": draft_data.get("subject")
                            },
                            record_count=1,
                            retrieval_time_ms=retrieval_time_ms
                        )
                    else:
                        context_repo.save_context(
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="email_draft",
                            query_text=user_message,
                            payload={
                                "lead_id": draft_data.get("lead_id"),
                                "lead_name": draft_data.get("lead_name"),
                                "template_type": draft_data.get("template_used"),
                                "subject": draft_data.get("subject")
                            },
                            record_count=1,
                            retrieval_time_ms=retrieval_time_ms
                        )
                except Exception as save_error:
                    logger.error(f"[EMAIL_DRAFT] Background context save failed: {save_error}", exc_info=True)
            
            # Create background task (fire-and-forget, no await)
            asyncio.create_task(save_context_async())
            logger.debug("[EMAIL_DRAFT] Context save scheduled in background task")
        else:
            # Existing sync behavior (blocking)
            if settings.ENABLE_ASYNC_DB:
                await asyncio.to_thread(
                    context_repo.save_context,
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="email_draft",
                    query_text=user_message,
                    payload={
                        "lead_id": draft_data.get("lead_id"),
                        "lead_name": draft_data.get("lead_name"),
                        "template_type": draft_data.get("template_used"),
                        "subject": draft_data.get("subject")
                    },
                    record_count=1,
                    retrieval_time_ms=retrieval_time_ms
                )
            else:
                context_repo.save_context(
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="email_draft",
                    query_text=user_message,
                    payload={
                        "lead_id": draft_data.get("lead_id"),
                        "lead_name": draft_data.get("lead_name"),
                        "template_type": draft_data.get("template_used"),
                        "subject": draft_data.get("subject")
                    },
                    record_count=1,
                    retrieval_time_ms=retrieval_time_ms
                )
        
        # Return formatted response
        return {
            "retrieved_context": draft_data,
            "source_type": "email_draft",
            "response": formatted_response  # Pre-formatted response, bypasses call_llm
        }
        
    except LeadNotFoundError as e:
        logger.warning(f"[EMAIL_DRAFT] Lead not found: {e}")
        
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
                                source_type="email_draft",
                                query_text=state.get("user_message", ""),
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=state.get("admin_id", "anonymous"),
                                source_type="email_draft",
                                query_text=state.get("user_message", ""),
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"[EMAIL_DRAFT] Background error context save failed: {save_error}", exc_info=True)
                
                asyncio.create_task(save_error_context_async())
            else:
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="email_draft",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="email_draft",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
        except:
            pass
        
        return {
            "retrieved_context": [],
            "source_type": "email_draft",
            "response": "Lead not found. Please check the lead name or ID and try again."
        }
        
    except Exception as e:
        logger.error(f"[EMAIL_DRAFT] Error generating email draft: {e}", exc_info=True)
        
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
                                source_type="email_draft",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="email_draft",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"[EMAIL_DRAFT] Background error context save failed: {save_error}", exc_info=True)
                
                asyncio.create_task(save_error_context_async())
            else:
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="email_draft",
                        query_text=query,
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="email_draft",
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
            "source_type": "email_draft",
            "response": "I encountered an error while generating the email draft. Please try again."
        }

