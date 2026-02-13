"""
LangGraph node for sending emails to leads.
Extracts lead identifier and email content, then sends via SMTP.
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
import re

logger = logging.getLogger(__name__)


def extract_email_content_from_state(state: AgentState) -> tuple[str, str]:
    """
    Extract subject and body from state.
    Checks retrieved_context for previous email draft.
    
    Returns:
        Tuple of (subject, body) or (None, None) if not found
    """
    # Check if there's a previous email draft in retrieved_context
    retrieved_context = state.get("retrieved_context")
    
    if isinstance(retrieved_context, dict):
        # Check if it's an email draft
        if retrieved_context.get("type") == "email_draft":
            subject = retrieved_context.get("subject", "")
            body = retrieved_context.get("body", "")
            if subject and body:
                return subject, body
    
    # Try to extract from conversation history (last assistant response)
    conversation_history = state.get("conversation_history", [])
    if conversation_history:
        # Look for email draft format in last response
        last_response = conversation_history[-1].get("assistant_response", "")
        
        # Try to extract subject and body from formatted response
        # Format: "Email Draft Generated...\n\nTo: ...\nSubject: ...\n\nBody:\n..."
        subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', last_response, re.MULTILINE)
        body_match = re.search(r'Body:\s*(.+?)(?:\nNote:|$)', last_response, re.DOTALL)
        
        if subject_match and body_match:
            subject = subject_match.group(1).strip()
            body = body_match.group(1).strip()
            if subject and body:
                return subject, body
    
    return None, None


async def send_email_node(state: AgentState) -> Dict[str, Any]:
    """
    Sends email to a lead.
    
    This node:
    1. Extracts lead identifier from user message
    2. Extracts subject and body from previous draft or state
    3. Calls EmailDraftService.send_email_to_lead()
    4. Returns formatted response
    """
    try:
        session_id = state.get("session_id")
        admin_id = state.get("admin_id", "anonymous")
        user_message = state.get("user_message", "")
        
        logger.info(f"[SEND_EMAIL] Processing send email request: {user_message[:100]}...")
        
        retrieval_start = time.time()
        
        # Initialize service
        service = EmailDraftService()
        
        # Extract lead identifier from query using the proven LeadSummaryService extraction logic
        # This ensures consistent behavior with lead summary and email draft features
        logger.info(f"[SEND_EMAIL] STEP 1: Extracting lead identifier from query: '{user_message}'")
        lead_identifier = service.lead_summary_service._extract_lead_identifier(user_message)
        logger.info(f"[SEND_EMAIL] STEP 1 RESULT: Extracted identifier: '{lead_identifier}' (type: {type(lead_identifier)})")
        
        if not lead_identifier:
            # Try to extract from previous context
            logger.info(f"[SEND_EMAIL] STEP 1 FALLBACK: Checking previous context for lead identifier")
            retrieved_context = state.get("retrieved_context")
            if isinstance(retrieved_context, dict):
                lead_id = retrieved_context.get("lead_id")
                lead_name = retrieved_context.get("lead_name")
                logger.info(f"[SEND_EMAIL] STEP 1 FALLBACK: Found lead_id={lead_id}, lead_name={lead_name}")
                if lead_id:
                    lead_identifier = str(lead_id)
                    logger.info(f"[SEND_EMAIL] STEP 1 FALLBACK: Using lead_id from context: '{lead_identifier}'")
                elif lead_name:
                    lead_identifier = lead_name
                    logger.info(f"[SEND_EMAIL] STEP 1 FALLBACK: Using lead_name from context: '{lead_identifier}'")
        
        if not lead_identifier:
            logger.warning(f"[SEND_EMAIL] STEP 1 FAILED: Could not extract lead identifier from query: {user_message}")
            return {
                "retrieved_context": [],
                "source_type": "send_email",
                "response": "I couldn't identify which lead you want to send the email to. Please specify the lead name or ID, for example: 'Send email to lead John Doe' or 'Send email for lead ID 132'."
            }
        
        # Clean identifier before use (strip quotes and whitespace)
        cleaned_identifier = lead_identifier.strip().strip('"').strip("'").strip()
        logger.info(f"[SEND_EMAIL] STEP 2: Cleaned identifier: '{cleaned_identifier}' (original: '{lead_identifier}')")
        logger.info(f"[SEND_EMAIL] STEP 2: Identifier type check - isdigit: {cleaned_identifier.isdigit()}, is_numeric: {service.lead_summary_service._is_numeric(cleaned_identifier)}")
        
        # Extract email content (subject and body)
        subject, body = extract_email_content_from_state(state)
        
        # If no email content found, try template-based sending
        if not subject or not body:
            logger.info(f"[SEND_EMAIL] STEP 3: No email content found in state, using template-based sending")
            logger.info(f"[SEND_EMAIL] STEP 3: Calling send_template_email_to_lead with identifier: '{cleaned_identifier}'")
            
            # Send template-based email (use cleaned identifier)
            try:
                if settings.ENABLE_ASYNC_DB:
                    logger.info(f"[SEND_EMAIL] STEP 3: Using async DB mode")
                    send_result = await asyncio.to_thread(
                        service.send_template_email_to_lead,
                        cleaned_identifier,  # Use cleaned identifier
                        user_message
                    )
                else:
                    logger.info(f"[SEND_EMAIL] STEP 3: Using sync DB mode")
                    send_result = service.send_template_email_to_lead(cleaned_identifier, user_message)  # Use cleaned identifier
                
                logger.info(f"[SEND_EMAIL] STEP 3 RESULT: Template email send result - Success: {send_result.get('success')}, Lead ID: {send_result.get('lead_id')}, Error: {send_result.get('error')}")
            except LeadNotFoundError as e:
                logger.error(f"[SEND_EMAIL] STEP 3 ERROR: LeadNotFoundError in send_template_email_to_lead: {e}")
                logger.error(f"[SEND_EMAIL] STEP 3 ERROR: Exception type: {type(e)}")
                logger.error(f"[SEND_EMAIL] STEP 3 ERROR: Identifier used: '{cleaned_identifier}'")
                raise
            except Exception as e:
                logger.error(f"[SEND_EMAIL] STEP 3 ERROR: Exception in send_template_email_to_lead: {e}", exc_info=True)
                raise
        else:
            logger.info(f"[SEND_EMAIL] STEP 3: Extracted email content - Subject: '{subject[:50]}...'")
            logger.info(f"[SEND_EMAIL] STEP 3: Calling send_email_to_lead with identifier: '{cleaned_identifier}'")
            
            # Send email with provided content (use cleaned identifier)
            try:
                if settings.ENABLE_ASYNC_DB:
                    send_result = await asyncio.to_thread(
                        service.send_email_to_lead,
                        cleaned_identifier,  # Use cleaned identifier
                        subject,
                        body
                    )
                else:
                    send_result = service.send_email_to_lead(cleaned_identifier, subject, body)  # Use cleaned identifier
            except Exception as e:
                logger.error(f"[SEND_EMAIL] STEP 3 ERROR: Exception in send_email_to_lead: {e}", exc_info=True)
                raise
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Format response
        if send_result.get("status") == "success":
            lead_name = send_result.get("lead_name", "Lead")
            to_email = send_result.get("to", "N/A")
            formatted_response = f"Email successfully sent to {lead_name} ({to_email})"
        else:
            error_msg = send_result.get("error", "Unknown error")
            lead_name = send_result.get("lead_name", "Lead")
            formatted_response = f"Failed to send email to {lead_name}. Reason: {error_msg}"
        
        logger.info(
            f"[SEND_EMAIL] Email send completed in {retrieval_time_ms}ms - Status: {send_result.get('status')}"
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
                            source_type="send_email",
                            query_text=user_message,
                            payload=send_result,
                            record_count=1 if send_result.get("status") == "success" else 0,
                            retrieval_time_ms=retrieval_time_ms,
                            error_message=send_result.get("error")
                        )
                    else:
                        context_repo.save_context(
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="send_email",
                            query_text=user_message,
                            payload=send_result,
                            record_count=1 if send_result.get("status") == "success" else 0,
                            retrieval_time_ms=retrieval_time_ms,
                            error_message=send_result.get("error")
                        )
                except Exception as save_error:
                    logger.error(f"[SEND_EMAIL] Background context save failed: {save_error}", exc_info=True)
            
            # Create background task (fire-and-forget, no await)
            asyncio.create_task(save_context_async())
            logger.debug("[SEND_EMAIL] Context save scheduled in background task")
        else:
            # Existing sync behavior (blocking)
            if settings.ENABLE_ASYNC_DB:
                await asyncio.to_thread(
                    context_repo.save_context,
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="send_email",
                    query_text=user_message,
                    payload=send_result,
                    record_count=1 if send_result.get("status") == "success" else 0,
                    retrieval_time_ms=retrieval_time_ms,
                    error_message=send_result.get("error")
                )
            else:
                context_repo.save_context(
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="send_email",
                    query_text=user_message,
                    payload=send_result,
                    record_count=1 if send_result.get("status") == "success" else 0,
                    retrieval_time_ms=retrieval_time_ms,
                    error_message=send_result.get("error")
                )
        
        # Return formatted response
        return {
            "retrieved_context": send_result,
            "source_type": "send_email",
            "response": formatted_response  # Pre-formatted response, bypasses call_llm
        }
        
    except LeadNotFoundError as e:
        logger.error(f"[SEND_EMAIL] LeadNotFoundError caught: {e}")
        logger.error(f"[SEND_EMAIL] Exception type: {type(e)}")
        logger.error(f"[SEND_EMAIL] Exception args: {e.args}")
        logger.error(f"[SEND_EMAIL] User message was: {state.get('user_message', 'N/A')}")
        logger.error(f"[SEND_EMAIL] Extracted identifier was: {locals().get('cleaned_identifier', 'N/A')}")
        
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
                                source_type="send_email",
                                query_text=state.get("user_message", ""),
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=state.get("admin_id", "anonymous"),
                                source_type="send_email",
                                query_text=state.get("user_message", ""),
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"[SEND_EMAIL] Background error context save failed: {save_error}", exc_info=True)
                
                asyncio.create_task(save_error_context_async())
            else:
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="send_email",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=state.get("admin_id", "anonymous"),
                        source_type="send_email",
                        query_text=state.get("user_message", ""),
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
        except:
            pass
        
        return {
            "retrieved_context": [],
            "source_type": "send_email",
            "response": "Lead not found. Please check the lead name or ID and try again."
        }
        
    except Exception as e:
        logger.error(f"[SEND_EMAIL] Error sending email: {e}", exc_info=True)
        
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
                                source_type="send_email",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="send_email",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"[SEND_EMAIL] Background error context save failed: {save_error}", exc_info=True)
                
                asyncio.create_task(save_error_context_async())
            else:
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="send_email",
                        query_text=query,
                        payload={"error": str(e)},
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="send_email",
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
            "source_type": "send_email",
            "response": "I encountered an error while sending the email. Please try again."
        }

