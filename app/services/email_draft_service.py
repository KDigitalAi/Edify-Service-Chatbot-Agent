"""
Smart Email Draft Assistant Service
Generates professional email drafts for leads based on context.
No database writes - only generates drafts.
"""

from typing import Dict, Any, List, Optional
from app.db.supabase import get_edify_supabase_client
from app.llm.openai_client import OpenAIClient
from app.services.lead_summary_service import LeadSummaryService, LeadNotFoundError
from app.services.email_sender_service import EmailSenderService
from app.core.config import settings
from datetime import datetime, timedelta, timezone
import logging
import re

logger = logging.getLogger(__name__)


class EmailDraftService:
    """
    Service for generating email drafts.
    Fetches lead context and generates appropriate email templates.
    """
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
        self.llm_client = OpenAIClient()
        self.lead_summary_service = LeadSummaryService()
        self.email_sender_service = EmailSenderService()
    
    def _get_latest_interaction(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent interaction for a lead.
        Checks calls, emails, meetings, notes and returns the latest one.
        """
        try:
            # Fetch all activities
            calls = self.lead_summary_service._fetch_calls(lead_id)
            emails = self.lead_summary_service._fetch_emails(lead_id)
            meetings = self.lead_summary_service._fetch_meetings(lead_id)
            notes = self.lead_summary_service._fetch_notes(lead_id)
            
            # Combine all interactions with type marker
            all_interactions = []
            
            for call in calls:
                all_interactions.append({
                    "type": "call",
                    "date": call.get("created_at"),
                    "data": call
                })
            
            for email in emails:
                all_interactions.append({
                    "type": "email",
                    "date": email.get("created_at"),
                    "data": email
                })
            
            for meeting in meetings:
                all_interactions.append({
                    "type": "meeting",
                    "date": meeting.get("created_at"),
                    "data": meeting
                })
            
            for note in notes:
                all_interactions.append({
                    "type": "note",
                    "date": note.get("created_at"),
                    "data": note
                })
            
            # Sort by date descending (most recent first)
            all_interactions.sort(key=lambda x: x.get("date") or "", reverse=True)
            
            # Return latest interaction if exists
            if all_interactions:
                return all_interactions[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error fetching latest interaction for lead {lead_id}: {e}")
            return None
    
    def _determine_template_type(self, lead: Dict[str, Any], latest_interaction: Optional[Dict[str, Any]]) -> str:
        """
        Determine email template type based on lead context and latest interaction.
        Returns: "follow_up", "proposal", "re_engagement", "meeting_confirmation", "objection_handling"
        """
        # If no interaction, use re-engagement
        if not latest_interaction:
            return "re_engagement"
        
        interaction_type = latest_interaction.get("type")
        interaction_data = latest_interaction.get("data", {})
        
        # Check for meeting scheduled
        if interaction_type == "meeting":
            meeting_name = interaction_data.get("meeting_name", "").lower()
            start_time = interaction_data.get("start_time")
            if start_time:
                return "meeting_confirmation"
        
        # Check for objection mentions in notes or calls
        if interaction_type in ["note", "call"]:
            content = ""
            if interaction_type == "note":
                content = interaction_data.get("content", "").lower()
            elif interaction_type == "call":
                # Check call notes or status
                content = str(interaction_data.get("status", "")).lower()
            
            objection_keywords = ["price", "expensive", "cost", "budget", "cheaper", "objection", "concern"]
            if any(keyword in content for keyword in objection_keywords):
                return "objection_handling"
        
        # Check opportunity status
        opportunity_status = lead.get("opportunity_status", "").lower()
        if "visiting" in opportunity_status or "proposal" in opportunity_status:
            return "proposal"
        
        # Check if last interaction was a call with no follow-up
        if interaction_type == "call":
            # Check if there's a recent email after this call
            call_date = interaction_data.get("created_at")
            if call_date:
                # Simple check: if call was recent and no email after, use follow-up
                return "follow_up"
        
        # Default: follow-up email
        return "follow_up"
    
    def generate_email_draft(self, lead_identifier: str) -> Dict[str, Any]:
        """
        Generate email draft for a lead.
        
        Args:
            lead_identifier: Lead ID (numeric) or lead name (string)
            
        Returns:
            Dictionary with email draft:
            {
                "type": "email_draft",
                "template_used": "follow_up" | "proposal" | etc.,
                "subject": "Email subject",
                "body": "Email body",
                "lead_name": "Lead name",
                "lead_email": "Lead email"
            }
            
        Raises:
            LeadNotFoundError: If lead is not found
        """
        try:
            # Fetch lead information
            summary_data = self.lead_summary_service.get_lead_activity_summary(lead_identifier)
            lead = summary_data.get("lead", {})
            
            if not lead:
                raise LeadNotFoundError(f"Lead not found: {lead_identifier}")
            
            lead_id = lead.get("id")
            if not lead_id:
                raise LeadNotFoundError(f"Lead record missing ID: {lead_identifier}")
            
            logger.info(f"Generating email draft for lead ID {lead_id} (name: {lead.get('name', 'N/A')})")
            
            # Get latest interaction
            latest_interaction = self._get_latest_interaction(lead_id)
            
            # Determine template type
            template_type = self._determine_template_type(lead, latest_interaction)
            
            logger.info(f"Selected template type: {template_type} for lead {lead_id}")
            
            # Generate email draft using LLM
            email_draft = self._generate_draft_with_llm(lead, latest_interaction, template_type)
            
            return {
                "type": "email_draft",
                "template_used": template_type,
                "subject": email_draft.get("subject", ""),
                "body": email_draft.get("body", ""),
                "lead_name": lead.get("name", "N/A"),
                "lead_email": lead.get("email", "N/A"),
                "lead_id": lead_id
            }
            
        except LeadNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error generating email draft: {e}", exc_info=True)
            raise
    
    def _generate_draft_with_llm(self, lead: Dict[str, Any], latest_interaction: Optional[Dict[str, Any]], template_type: str) -> Dict[str, Any]:
        """
        Generate email draft using LLM based on template type.
        """
        # Build system prompt
        system_prompt = """You are a CRM sales email assistant. Generate a professional email draft for sales representatives.

CRITICAL RULES:
1. Use ONLY the provided lead information. Do NOT invent any details.
2. Do NOT hallucinate company names, products, or specific details not provided.
3. Keep tone professional, friendly, and persuasive.
4. Keep email concise (2-3 paragraphs maximum).
5. Include a clear call-to-action.
6. Personalize based on lead's name and context.

Return ONLY a JSON object with this exact format:
{
    "subject": "Email subject line",
    "body": "Email body text"
}

Do NOT include any other text or explanation. Only return the JSON."""
        
        # Build context based on template type
        context_info = self._build_context_for_template(lead, latest_interaction, template_type)
        
        # Build user prompt
        user_prompt = f"""Generate a {template_type.replace('_', ' ')} email draft for the following lead:

LEAD INFORMATION:
Name: {lead.get('name', 'N/A')}
Email: {lead.get('email', 'N/A')}
Phone: {lead.get('phone', 'N/A')}
Status: {lead.get('status', 'N/A')}
Stage: {lead.get('stage', 'N/A')}
Owner: {lead.get('owner', 'N/A')}

{context_info}

Generate a professional email draft. Return ONLY the JSON object with subject and body fields."""
        
        try:
            # Call LLM
            llm_response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_input=user_prompt
            )
            
            # Parse JSON response
            import json
            # Try to extract JSON from response (LLM might add extra text)
            json_match = re.search(r'\{[^{}]*"subject"[^{}]*"body"[^{}]*\}', llm_response, re.DOTALL)
            if json_match:
                draft_json = json.loads(json_match.group(0))
            else:
                # Fallback: try parsing entire response
                draft_json = json.loads(llm_response.strip())
            
            return {
                "subject": draft_json.get("subject", "Follow-up"),
                "body": draft_json.get("body", "Dear [Name],\n\n[Email body]")
            }
            
        except Exception as e:
            logger.error(f"Error generating email draft with LLM: {e}", exc_info=True)
            # Fallback to template-based generation
            return self._generate_fallback_draft(lead, template_type)
    
    def _build_context_for_template(self, lead: Dict[str, Any], latest_interaction: Optional[Dict[str, Any]], template_type: str) -> str:
        """Build context information for LLM based on template type."""
        context_lines = []
        
        if latest_interaction:
            interaction_type = latest_interaction.get("type")
            interaction_data = latest_interaction.get("data", {})
            interaction_date = latest_interaction.get("date", "N/A")
            
            context_lines.append(f"\nLATEST INTERACTION:")
            context_lines.append(f"Type: {interaction_type}")
            context_lines.append(f"Date: {interaction_date}")
            
            if interaction_type == "call":
                context_lines.append(f"Status: {interaction_data.get('status', 'N/A')}")
                context_lines.append(f"Direction: {interaction_data.get('direction', 'N/A')}")
            elif interaction_type == "email":
                context_lines.append(f"Subject: {interaction_data.get('subject', 'N/A')}")
            elif interaction_type == "meeting":
                context_lines.append(f"Meeting: {interaction_data.get('meeting_name', 'N/A')}")
                context_lines.append(f"Location: {interaction_data.get('location', 'N/A')}")
            elif interaction_type == "note":
                content = interaction_data.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                context_lines.append(f"Note: {content}")
        
        # Add template-specific context
        if template_type == "follow_up":
            context_lines.append("\nTEMPLATE TYPE: Follow-Up Email")
            context_lines.append("Purpose: Follow up on recent interaction, check interest, move conversation forward.")
        elif template_type == "proposal":
            context_lines.append("\nTEMPLATE TYPE: Proposal/Pricing Email")
            context_lines.append("Purpose: Present proposal or pricing information, highlight value proposition.")
        elif template_type == "re_engagement":
            context_lines.append("\nTEMPLATE TYPE: Re-Engagement Email")
            context_lines.append("Purpose: Re-engage after period of inactivity, check if still interested.")
        elif template_type == "meeting_confirmation":
            context_lines.append("\nTEMPLATE TYPE: Meeting Confirmation Email")
            context_lines.append("Purpose: Confirm meeting details, provide agenda, express excitement.")
        elif template_type == "objection_handling":
            context_lines.append("\nTEMPLATE TYPE: Objection Handling Email")
            context_lines.append("Purpose: Address concerns or objections, provide reassurance, offer solutions.")
        
        return "\n".join(context_lines)
    
    def _generate_fallback_draft(self, lead: Dict[str, Any], template_type: str) -> Dict[str, Any]:
        """Generate fallback email draft if LLM fails."""
        lead_name = lead.get("name", "Valued Customer")
        
        templates = {
            "follow_up": {
                "subject": f"Following up - {lead_name}",
                "body": f"Dear {lead_name},\n\nI wanted to follow up on our recent conversation. I'm here to answer any questions you may have.\n\nLooking forward to hearing from you.\n\nBest regards"
            },
            "proposal": {
                "subject": f"Proposal for {lead_name}",
                "body": f"Dear {lead_name},\n\nThank you for your interest. I've prepared a proposal tailored to your needs.\n\nPlease let me know if you have any questions.\n\nBest regards"
            },
            "re_engagement": {
                "subject": f"Reconnecting - {lead_name}",
                "body": f"Dear {lead_name},\n\nI wanted to reconnect and see if you're still interested in learning more.\n\nI'm here to help whenever you're ready.\n\nBest regards"
            },
            "meeting_confirmation": {
                "subject": f"Meeting Confirmation - {lead_name}",
                "body": f"Dear {lead_name},\n\nI'm confirming our upcoming meeting. I'm looking forward to our discussion.\n\nBest regards"
            },
            "objection_handling": {
                "subject": f"Addressing your questions - {lead_name}",
                "body": f"Dear {lead_name},\n\nI wanted to address the questions you raised. I believe we can find a solution that works for you.\n\nLet's discuss this further.\n\nBest regards"
            }
        }
        
        return templates.get(template_type, templates["follow_up"])
    
    def _get_template(self, template_type: str, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get email template based on template type.
        
        Args:
            template_type: "introduction", "followup", or "reminder"
            lead: Lead dictionary with name field
            
        Returns:
            Dictionary with subject, body, and template_used:
            {
                "subject": "...",
                "body": "...",
                "template_used": "introduction/followup/reminder"
            }
        """
        lead_name = lead.get("name", "Valued Customer")
        
        templates = {
            "introduction": {
                "subject": f"Introduction Request – {lead_name}",
                "body": f"Hi {lead_name},\n\nI hope this email finds you well.\n\nI wanted to reach out to introduce ourselves and see if there might be a fit for a conversation.\n\nWould you have a few minutes for a short call this week?\n\nBest regards"
            },
            "followup": {
                "subject": f"Follow-up After Demo – {lead_name}",
                "body": f"Hi {lead_name},\n\nThank you for attending the demo session. We hope it was helpful.\n\nIf you have any questions or would like to schedule a follow-up call, please reply to this email.\n\nBest regards"
            },
            "reminder": {
                "subject": f"Meeting Reminder – {lead_name}",
                "body": f"Hi {lead_name},\n\nThis is a reminder about our scheduled meeting.\n\nPlease confirm your availability or suggest an alternative time.\n\nBest regards"
            }
        }
        
        # Default to introduction if template type not found
        template = templates.get(template_type, templates["introduction"])
        
        return {
            "subject": template["subject"],
            "body": template["body"],
            "template_used": template_type
        }
    
    def _select_template_type(self, user_message: str) -> str:
        """
        Select template type based on user message keywords.
        
        Args:
            user_message: User's query message
            
        Returns:
            Template type: "introduction", "followup", or "reminder"
        """
        normalized = user_message.lower().strip()
        
        # Check for introduction keywords
        if "introduction" in normalized:
            return "introduction"
        
        # Check for follow-up keywords
        if "follow up" in normalized or "follow-up" in normalized or "followup" in normalized:
            return "followup"
        
        # Check for meeting reminder keywords
        if "meeting reminder" in normalized or "reminder" in normalized:
            return "reminder"
        
        # Default to introduction
        return "introduction"
    
    def send_template_email_to_lead(self, lead_identifier: str, user_message: str = "") -> Dict[str, Any]:
        """
        Send template-based email to a lead.
        
        Args:
            lead_identifier: Lead ID (numeric) or lead name (string)
            user_message: User's query message (for template selection)
            
        Returns:
            Dictionary with result:
            {
                "type": "email_sent",
                "to": "lead@email.com",
                "subject": "...",
                "status": "success" | "failed",
                "error": None or error_message,
                "lead_id": int,
                "lead_name": str,
                "template_used": "introduction/followup/reminder",
                "success": True/False
            }
            
        Raises:
            LeadNotFoundError: If lead is not found
        """
        try:
            logger.info(f"[EMAIL_DRAFT] send_template_email_to_lead called with identifier: '{lead_identifier}' (type: {type(lead_identifier)})")
            
            # CRITICAL: Clean identifier before passing to get_lead_activity_summary
            # This ensures consistency even if caller didn't clean it
            cleaned_identifier = lead_identifier.strip().strip('"').strip("'").strip()
            logger.info(f"[EMAIL_DRAFT] Cleaned identifier: '{cleaned_identifier}' (original: '{lead_identifier}')")
            
            # Fetch lead information
            logger.info(f"[EMAIL_DRAFT] STEP 1: Calling get_lead_activity_summary with cleaned identifier: '{cleaned_identifier}'")
            try:
                summary_data = self.lead_summary_service.get_lead_activity_summary(cleaned_identifier)
                logger.info(f"[EMAIL_DRAFT] STEP 1 RESULT: get_lead_activity_summary returned data: {bool(summary_data)}")
            except LeadNotFoundError as e:
                logger.error(f"[EMAIL_DRAFT] STEP 1 ERROR: LeadNotFoundError raised from get_lead_activity_summary")
                logger.error(f"[EMAIL_DRAFT] STEP 1 ERROR: Exception: {e}")
                logger.error(f"[EMAIL_DRAFT] STEP 1 ERROR: Identifier used: '{cleaned_identifier}'")
                raise
            except Exception as e:
                logger.error(f"[EMAIL_DRAFT] STEP 1 ERROR: Unexpected exception: {e}", exc_info=True)
                raise
            
            lead = summary_data.get("lead", {})
            logger.info(f"[EMAIL_DRAFT] STEP 2: Extracted lead from summary_data: {bool(lead)}, lead_id: {lead.get('id') if lead else None}")
            
            if not lead:
                logger.error(f"[EMAIL_DRAFT] STEP 2 FAILED: Lead not found in summary_data for identifier: '{cleaned_identifier}'")
                raise LeadNotFoundError(f"Lead not found: {cleaned_identifier}")
            
            lead_id = lead.get("id")
            lead_name = lead.get("name", "N/A")
            lead_email = lead.get("email")
            logger.info(f"[EMAIL_DRAFT] STEP 3: Lead found - ID: {lead_id}, Name: {lead_name}, Email: {lead_email}")
            
            if not lead_id:
                raise LeadNotFoundError(f"Lead record missing ID: {lead_identifier}")
            
            if not lead_email:
                return {
                    "type": "email_sent",
                    "status": "failed",
                    "error": f"Lead {lead_name} does not have an email address",
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "success": False
                }
            
            # Select template type based on user message
            template_type = self._select_template_type(user_message)
            
            # Get template
            template = self._get_template(template_type, lead)
            subject = template["subject"]
            body = template["body"]
            template_used = template["template_used"]
            
            logger.info(f"Sending {template_used} template email to lead ID {lead_id} ({lead_name}) at {lead_email}")
            
            # Send email via SMTP
            send_result = self.email_sender_service.send_email(
                to_email=lead_email,
                subject=subject,
                body=body
            )
            
            # If email sent successfully, store record in emails table
            if send_result.get("success"):
                try:
                    # Insert into emails table
                    email_record = {
                        "to": lead_email,
                        "from": settings.SMTP_USERNAME,
                        "subject": subject,
                        "body": body,
                        "lead_id": lead_id,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    response = self.supabase.table("emails").insert(email_record).execute()
                    
                    if response.data:
                        logger.info(f"Email record stored in database for lead {lead_id}")
                    else:
                        logger.warning(f"Email sent but failed to store record in database for lead {lead_id}")
                
                except Exception as db_error:
                    # Log error but don't fail the send operation
                    logger.error(f"Error storing email record in database: {db_error}", exc_info=True)
                
                return {
                    "type": "email_sent",
                    "to": lead_email,
                    "subject": subject,
                    "status": "success",
                    "error": None,
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "template_used": template_used,
                    "success": True
                }
            else:
                # Email sending failed
                error_msg = send_result.get("error", "Unknown error")
                logger.error(f"Failed to send email to {lead_email}: {error_msg}")
                
                return {
                    "type": "email_sent",
                    "to": lead_email,
                    "subject": subject,
                    "status": "failed",
                    "error": error_msg,
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "template_used": template_used,
                    "success": False
                }
            
        except LeadNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error sending template email to lead: {e}", exc_info=True)
            raise
    
    def send_email_to_lead(self, lead_identifier: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send email to a lead and store record in emails table.
        
        Args:
            lead_identifier: Lead ID (numeric) or lead name (string)
            subject: Email subject
            body: Email body
            
        Returns:
            Dictionary with result:
            {
                "type": "email_sent",
                "to": "lead@email.com",
                "subject": "...",
                "status": "success" | "failed",
                "error": None or error_message,
                "lead_id": int,
                "lead_name": str
            }
            
        Raises:
            LeadNotFoundError: If lead is not found
        """
        try:
            # Fetch lead information (reuse existing logic)
            summary_data = self.lead_summary_service.get_lead_activity_summary(lead_identifier)
            lead = summary_data.get("lead", {})
            
            if not lead:
                raise LeadNotFoundError(f"Lead not found: {lead_identifier}")
            
            lead_id = lead.get("id")
            lead_name = lead.get("name", "N/A")
            lead_email = lead.get("email")
            
            if not lead_id:
                raise LeadNotFoundError(f"Lead record missing ID: {lead_identifier}")
            
            if not lead_email:
                return {
                    "type": "email_sent",
                    "status": "failed",
                    "error": f"Lead {lead_name} does not have an email address",
                    "lead_id": lead_id,
                    "lead_name": lead_name
                }
            
            logger.info(f"Sending email to lead ID {lead_id} ({lead_name}) at {lead_email}")
            
            # Validate subject and body
            if not subject or not subject.strip():
                return {
                    "type": "email_sent",
                    "status": "failed",
                    "error": "Email subject cannot be empty",
                    "lead_id": lead_id,
                    "lead_name": lead_name
                }
            
            if not body or not body.strip():
                return {
                    "type": "email_sent",
                    "status": "failed",
                    "error": "Email body cannot be empty",
                    "lead_id": lead_id,
                    "lead_name": lead_name
                }
            
            # Send email via SMTP
            send_result = self.email_sender_service.send_email(
                to_email=lead_email,
                subject=subject,
                body=body
            )
            
            # If email sent successfully, store record in emails table
            if send_result.get("success"):
                try:
                    # Insert into emails table
                    email_record = {
                        "to": lead_email,
                        "from": settings.SMTP_USERNAME,
                        "subject": subject,
                        "body": body,
                        "lead_id": lead_id,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    response = self.supabase.table("emails").insert(email_record).execute()
                    
                    if response.data:
                        logger.info(f"Email record stored in database for lead {lead_id}")
                    else:
                        logger.warning(f"Email sent but failed to store record in database for lead {lead_id}")
                
                except Exception as db_error:
                    # Log error but don't fail the send operation
                    logger.error(f"Error storing email record in database: {db_error}", exc_info=True)
                
                return {
                    "type": "email_sent",
                    "to": lead_email,
                    "subject": subject,
                    "status": "success",
                    "error": None,
                    "lead_id": lead_id,
                    "lead_name": lead_name
                }
            else:
                # Email sending failed
                error_msg = send_result.get("error", "Unknown error")
                logger.error(f"Failed to send email to {lead_email}: {error_msg}")
                
                return {
                    "type": "email_sent",
                    "to": lead_email,
                    "subject": subject,
                    "status": "failed",
                    "error": error_msg,
                    "lead_id": lead_id,
                    "lead_name": lead_name
                }
            
        except LeadNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error sending email to lead: {e}", exc_info=True)
            raise

