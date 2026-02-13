"""
Lead Activity Summary Service
Fetches lead information and all related activities (calls, emails, meetings, notes).
Fully dynamic - works for any lead by ID or name.
"""

from typing import Dict, Any, List, Optional
from app.db.supabase import get_edify_supabase_client
from app.llm.openai_client import OpenAIClient
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class LeadNotFoundError(Exception):
    """Custom exception for when lead is not found."""
    pass


class LeadSummaryService:
    """
    Service for generating lead activity summaries.
    Fetches lead and all related activities dynamically.
    No hardcoded values - works for all leads.
    """
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
        self.llm_client = OpenAIClient()
    
    def _is_numeric(self, identifier: str) -> bool:
        """
        Check if identifier is numeric (lead ID).
        Handles identifiers with quotes and whitespace.
        """
        if not identifier:
            return False
        
        # Strip whitespace and quotes before checking
        cleaned = identifier.strip().strip('"').strip("'").strip()
        
        try:
            int(cleaned)
            return True
        except ValueError:
            return False
    
    def _find_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Find lead by ID (dynamic - works for any lead ID).
        Uses exact match on ID column.
        """
        try:
            # Ensure lead_id is cleaned and converted to int
            cleaned_id = lead_id.strip().strip('"').strip("'").strip()
            lead_id_int = int(cleaned_id)
            
            logger.debug(f"[LEAD_SUMMARY] Querying leads table: id = {lead_id_int}")
            
            response = (
                self.supabase.table("leads")
                .select("*")
                .eq("id", lead_id_int)
                .single()
                .execute()
            )
            
            result = response.data if response.data else None
            if result:
                logger.info(f"[LEAD_SUMMARY] Successfully found lead by ID {lead_id_int}: {result.get('name', 'N/A')}")
            else:
                logger.warning(f"[LEAD_SUMMARY] No lead found with ID {lead_id_int}")
            
            return result
        except ValueError as e:
            logger.error(f"[LEAD_SUMMARY] Invalid lead ID format '{lead_id}': {e}")
            return None
        except Exception as e:
            logger.error(f"[LEAD_SUMMARY] Error fetching lead by ID {lead_id}: {e}", exc_info=True)
            return None
    
    def _find_lead_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find lead by name (case-insensitive search, dynamic).
        Uses ILIKE for case-insensitive partial matching.
        """
        try:
            # Clean name - strip quotes and whitespace
            cleaned_name = name.strip().strip('"').strip("'").strip()
            
            if not cleaned_name:
                logger.warning(f"[LEAD_SUMMARY] Empty name provided for search")
                return None
            
            logger.debug(f"[LEAD_SUMMARY] Querying leads table: name ILIKE '%{cleaned_name}%'")
            
            # Search for leads matching the name (case-insensitive)
            response = (
                self.supabase.table("leads")
                .select("*")
                .ilike("name", f"%{cleaned_name}%")
                .limit(1)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                result = response.data[0]
                logger.info(f"[LEAD_SUMMARY] Successfully found lead by name '{cleaned_name}': ID {result.get('id')}, Name: {result.get('name', 'N/A')}")
                return result
            
            logger.warning(f"[LEAD_SUMMARY] No lead found with name matching '{cleaned_name}'")
            return None
        except Exception as e:
            logger.error(f"[LEAD_SUMMARY] Error fetching lead by name '{name}': {e}", exc_info=True)
            return None
    
    def _extract_lead_identifier(self, query: str) -> Optional[str]:
        """
        Extract lead identifier from query dynamically.
        Handles various query formats:
        - "lead ID 123" or "ID 123" (prioritized)
        - "lead guna" or "guna"
        
        - "summary of lead 456"
        - "lead guna and lead id 132" (extracts ID 132)
        """
        # Normalize query
        query_lower = query.lower().strip()
        
        # Pattern 1: "lead ID 123" or "ID 123" (PRIORITIZE ID - most specific)
        # This handles cases like "lead guna and lead id 132" -> extracts "132"
        # Also handles "lead id: 132" (with colon)
        id_patterns = [
            r'lead\s+id\s*:?\s*(\d+)',  # "lead id 132" or "lead id: 132"
            r'\bid\s*:?\s*(\d+)',        # "id 132" or "id: 132" or "lead guna and lead id: 132"
            r'lead\s+(\d+)',             # "lead 132"
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, query_lower)
            if match:
                lead_id = match.group(1)
                logger.info(f"Extracted lead ID from query: {lead_id}")
                return lead_id
        
        # Pattern 2: Extract name after keywords (but stop at "and" if ID follows)
        # Handle "lead guna and lead id 132" -> extract "guna" first, but ID takes priority above
        # CRITICAL: Handle "lead name 'guna'" format - extract name from quotes
        name_patterns = [
            # Pattern 2a: "lead name 'guna'" or "lead name "guna"" - extract name from quotes
            r'lead\s+name\s+["\']([^"\']+)["\']',
            # Pattern 2b: "lead name guna" (without quotes)
            r'lead\s+name\s+(\w+)',
            # Pattern 2c: Other name patterns
            r'(?:summary|activity|full|history)\s+(?:of|for)\s+(?:lead\s+)?(.+?)(?:\s+and\s+lead\s+id|\s+and\s+id|\s|$)',
            r'lead\s+(?:summary|activity|full|history)\s+(?:of|for)\s+(.+?)(?:\s+and\s+lead\s+id|\s+and\s+id|\s|$)',
            r'lead\s+([a-zA-Z\s]+?)(?:\s+and\s+lead\s+id|\s+and\s+id|\s|$)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, query_lower)
            if match:
                name = match.group(1).strip()
                # Strip quotes if present (shouldn't be needed for pattern 2a, but safe)
                name = name.strip('"').strip("'").strip()
                # Remove common stop words (but not for pattern 2a/2b which already extracted cleanly)
                if not pattern.startswith(r'lead\s+name'):
                    name = re.sub(r'\b(summary|activity|full|history|of|for|the|a|an|name)\b', '', name).strip()
                # Remove "and" if present
                name = re.sub(r'\s+and\s+.*$', '', name).strip()
                if name and len(name) > 1:
                    logger.info(f"Extracted lead name from query: {name}")
                    return name
        
        # Pattern 3: If query is just a number, treat as ID
        if query.strip().isdigit():
            return query.strip()
        
        # Pattern 4: If query is just a name (no keywords), use it
        if len(query.split()) <= 3 and not any(keyword in query_lower for keyword in ['summary', 'activity', 'lead', 'id']):
            return query.strip()
        
        return None
    
    def _build_recent_activity_timeline(self, calls: List[Dict], emails: List[Dict], 
                                       meetings: List[Dict], notes: List[Dict]) -> List[Dict[str, Any]]:
        """
        Build unified timeline of all activities, sorted by date descending.
        Returns top 10 most recent activities.
        """
        timeline = []
        
        # Add calls
        for call in calls:
            timeline.append({
                "type": "call",
                "date": call.get("created_at"),
                "summary": self._format_call_summary(call)
            })
        
        # Add emails
        for email in emails:
            timeline.append({
                "type": "email",
                "date": email.get("created_at"),
                "summary": self._format_email_summary(email)
            })
        
        # Add meetings
        for meeting in meetings:
            timeline.append({
                "type": "meeting",
                "date": meeting.get("created_at"),
                "summary": self._format_meeting_summary(meeting)
            })
        
        # Add notes
        for note in notes:
            timeline.append({
                "type": "note",
                "date": note.get("created_at"),
                "summary": self._format_note_summary(note)
            })
        
        # Sort by date descending (most recent first)
        timeline.sort(key=lambda x: x.get("date") or "", reverse=True)
        
        # Return top 10
        return timeline[:10]
    
    def _format_call_summary(self, call: Dict[str, Any]) -> str:
        """Format call summary for timeline."""
        status = call.get("status", "N/A")
        direction = call.get("direction", "N/A")
        return f"{direction.capitalize()} call - {status}"
    
    def _format_email_summary(self, email: Dict[str, Any]) -> str:
        """Format email summary for timeline."""
        subject = email.get("subject", "No subject")
        if len(subject) > 50:
            subject = subject[:50] + "..."
        return f"Email: {subject}"
    
    def _format_meeting_summary(self, meeting: Dict[str, Any]) -> str:
        """Format meeting summary for timeline."""
        name = meeting.get("meeting_name", "Meeting")
        location = meeting.get("location", "")
        if location:
            return f"{name} - {location}"
        return name
    
    def _format_note_summary(self, note: Dict[str, Any]) -> str:
        """Format note summary for timeline."""
        content = note.get("content", "")
        if len(content) > 60:
            content = content[:60] + "..."
        return content if content else "Note"
    
    def get_lead_activity_summary(self, lead_identifier: str) -> Dict[str, Any]:
        """
        Get comprehensive activity summary for a lead (fully dynamic).
        
        Args:
            lead_identifier: Lead ID (numeric) or lead name (string)
            
        Returns:
            Structured dictionary:
            {
                "lead": {
                    "id": int,
                    "name": str,
                    "status": str,
                    "stage": str,
                    "source": str,
                    "created_at": str,
                    "updated_at": str
                },
                "activity_counts": {
                    "calls": int,
                    "emails": int,
                    "meetings": int,
                    "notes": int
                },
                "recent_activity": [
                    {
                        "type": "call/email/meeting/note",
                        "date": str,
                        "summary": str
                    }
                ],
                "calls": [...],
                "emails": [...],
                "meetings": [...],
                "notes": [...]
            }
            
        Raises:
            LeadNotFoundError: If lead is not found
        """
        try:
            # CRITICAL: Clean identifier - strip quotes, whitespace, and normalize
            # This ensures consistent behavior regardless of how identifier was extracted
            cleaned_identifier = lead_identifier.strip().strip('"').strip("'").strip()
            
            logger.info(f"[LEAD_SUMMARY] Fetching lead with cleaned identifier: '{cleaned_identifier}' (original: '{lead_identifier}')")
            
            # Dynamically identify lead (by ID or name)
            # PRIORITY: Check ID first (more specific and faster)
            if self._is_numeric(cleaned_identifier):
                logger.info(f"[LEAD_SUMMARY] Identifier is numeric, searching by ID: {cleaned_identifier}")
                lead = self._find_lead_by_id(cleaned_identifier)
                if lead:
                    logger.info(f"[LEAD_SUMMARY] Found lead by ID: {lead.get('id')} (name: {lead.get('name', 'N/A')})")
                else:
                    logger.warning(f"[LEAD_SUMMARY] Lead not found by ID: {cleaned_identifier}")
            else:
                logger.info(f"[LEAD_SUMMARY] Identifier is not numeric, searching by name (case-insensitive ILIKE): '{cleaned_identifier}'")
                lead = self._find_lead_by_name(cleaned_identifier)
                if lead:
                    logger.info(f"[LEAD_SUMMARY] Found lead by name: {lead.get('id')} (name: {lead.get('name', 'N/A')})")
                else:
                    logger.warning(f"[LEAD_SUMMARY] Lead not found by name: '{cleaned_identifier}'")
            
            if not lead:
                logger.error(f"[LEAD_SUMMARY] Lead not found - cleaned identifier: '{cleaned_identifier}', original: '{lead_identifier}'")
                raise LeadNotFoundError(f"Lead not found: {cleaned_identifier}")
            
            lead_id = lead.get("id")
            if not lead_id:
                raise LeadNotFoundError(f"Lead record missing ID: {lead_identifier}")
            
            logger.info(f"Found lead ID {lead_id} (name: {lead.get('name', 'N/A')}), fetching related activities...")
            
            # Fetch all related activities using lead_id (verified column name: lead_id)
            calls = self._fetch_calls(lead_id)
            emails = self._fetch_emails(lead_id)
            meetings = self._fetch_meetings(lead_id)
            notes = self._fetch_notes(lead_id)
            
            # Build activity counts
            activity_counts = {
                "calls": len(calls),
                "emails": len(emails),
                "meetings": len(meetings),
                "notes": len(notes)
            }
            
            # Build recent activity timeline (top 10, sorted by date)
            recent_activity = self._build_recent_activity_timeline(calls, emails, meetings, notes)
            
            logger.info(
                f"Lead {lead_id} activity summary: "
                f"{activity_counts['calls']} calls, {activity_counts['emails']} emails, "
                f"{activity_counts['meetings']} meetings, {activity_counts['notes']} notes"
            )
            
            # Return structured summary
            return {
                "lead": {
                    "id": lead.get("id"),
                    "name": lead.get("name"),
                    "status": lead.get("lead_status"),
                    "stage": lead.get("lead_stage"),
                    "source": lead.get("lead_source"),
                    "owner": lead.get("lead_owner"),
                    "email": lead.get("email"),
                    "phone": lead.get("phone"),
                    "created_at": lead.get("created_at"),
                    "updated_at": lead.get("updated_at")
                },
                "activity_counts": activity_counts,
                "recent_activity": recent_activity,
                "calls": calls,
                "emails": emails,
                "meetings": meetings,
                "notes": notes
            }
            
        except LeadNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching lead activity summary: {e}", exc_info=True)
            raise
    
    def _fetch_calls(self, lead_id: int) -> List[Dict[str, Any]]:
        """Fetch all calls related to lead (using lead_id foreign key)."""
        try:
            response = (
                self.supabase.table("calls")
                .select("*")
                .eq("lead_id", lead_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching calls for lead {lead_id}: {e}")
            return []
    
    def _fetch_emails(self, lead_id: int) -> List[Dict[str, Any]]:
        """Fetch all emails related to lead (using lead_id foreign key)."""
        try:
            response = (
                self.supabase.table("emails")
                .select("*")
                .eq("lead_id", lead_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching emails for lead {lead_id}: {e}")
            return []
    
    def _fetch_meetings(self, lead_id: int) -> List[Dict[str, Any]]:
        """Fetch all meetings related to lead (using lead_id foreign key)."""
        try:
            response = (
                self.supabase.table("meetings")
                .select("*")
                .eq("lead_id", lead_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching meetings for lead {lead_id}: {e}")
            return []
    
    def _fetch_notes(self, lead_id: int) -> List[Dict[str, Any]]:
        """Fetch all notes related to lead (using lead_id foreign key)."""
        try:
            response = (
                self.supabase.table("notes")
                .select("*")
                .eq("lead_id", lead_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching notes for lead {lead_id}: {e}")
            return []
    
    def format_lead_summary_with_llm(self, summary_data: Dict[str, Any]) -> str:
        """
        Format lead summary using LLM for natural language generation.
        LLM is used ONLY for formatting - no hallucination allowed.
        
        Args:
            summary_data: Dictionary from get_lead_activity_summary()
            
        Returns:
            Formatted summary string
        """
        # If no data, return simple message
        if not summary_data or not summary_data.get("lead"):
            return "Lead found but no data available."
        
        lead = summary_data.get("lead", {})
        activity_counts = summary_data.get("activity_counts", {})
        recent_activity = summary_data.get("recent_activity", [])
        calls = summary_data.get("calls", [])
        emails = summary_data.get("emails", [])
        meetings = summary_data.get("meetings", [])
        notes = summary_data.get("notes", [])
        
        # If no activity, return simple message without LLM
        total_activity = (
            activity_counts.get("calls", 0) +
            activity_counts.get("emails", 0) +
            activity_counts.get("meetings", 0) +
            activity_counts.get("notes", 0)
        )
        
        if total_activity == 0:
            lead_name = lead.get("name", "Unknown")
            lead_status = lead.get("status", "N/A")
            lead_owner = lead.get("owner", "N/A")
            return (
                f"Lead Information:\n"
                f"Lead: {lead_name}\n"
                f"Status: {lead_status}\n"
                f"Owner: {lead_owner}\n\n"
                f"Activity Overview:\n"
                f"- 0 Calls\n"
                f"- 0 Emails\n"
                f"- 0 Meetings\n"
                f"- 0 Notes\n\n"
                f"Lead found but no recorded activity (calls, emails, meetings, or notes)."
            )
        
        # Build system prompt (strict - no hallucination)
        system_prompt = """You are a CRM sales assistant. Generate a professional lead activity summary.

CRITICAL RULES:
1. Use ONLY the provided data. Do NOT invent or hallucinate any information.
2. If a field is missing or null, say "N/A" or omit it.
3. ALWAYS include Activity Overview section showing counts (even if 0).
4. ALWAYS include Recent Timeline section if activities exist (show up to 10 most recent).
5. Format the summary EXACTLY as shown below with these sections:
   - Lead Information (name, status, owner, contact info)
   - Activity Overview (REQUIRED - counts for each activity type)
   - Recent Timeline (only if activities exist)

Format the response EXACTLY as:

Lead Information:
Lead: [Name]
Status: [Status]
Owner: [Owner]
Email: [Email]
Phone: [Phone]

Activity Overview:
- [X] Calls (Last: [Date] – [Status] if available, otherwise just show count)
- [X] Emails Sent (Last: [Date] if available, otherwise just show count)
- [X] Meetings conducted
- [X] Notes recorded

Recent Timeline:
• [Date] – [Type] – [Description]
• [Date] – [Type] – [Description]
(Only include this section if there are activities in the timeline)

IMPORTANT: Always show Activity Overview section with counts. If all counts are 0, show "0 Calls, 0 Emails, 0 Meetings, 0 Notes".
Keep it concise, actionable, and professional. Do NOT add information not in the provided data."""
        
        # Build user prompt with structured data
        user_prompt = f"""Generate a professional summary for the following lead activity data:

LEAD INFORMATION:
Name: {lead.get('name', 'N/A')}
Status: {lead.get('status', 'N/A')}
Stage: {lead.get('stage', 'N/A')}
Source: {lead.get('source', 'N/A')}
Owner: {lead.get('owner', 'N/A')}
Email: {lead.get('email', 'N/A')}
Phone: {lead.get('phone', 'N/A')}
Created: {lead.get('created_at', 'N/A')}
Updated: {lead.get('updated_at', 'N/A')}

ACTIVITY COUNTS:
Calls: {activity_counts.get('calls', 0)}
Emails: {activity_counts.get('emails', 0)}
Meetings: {activity_counts.get('meetings', 0)}
Notes: {activity_counts.get('notes', 0)}

RECENT ACTIVITY TIMELINE (Most Recent First):
{self._format_timeline_for_llm(recent_activity)}

DETAILED ACTIVITIES:

CALLS ({activity_counts.get('calls', 0)} total):
{self._format_activities(calls, 'call')}

EMAILS ({activity_counts.get('emails', 0)} total):
{self._format_activities(emails, 'email')}

MEETINGS ({activity_counts.get('meetings', 0)} total):
{self._format_activities(meetings, 'meeting')}

NOTES ({activity_counts.get('notes', 0)} total):
{self._format_activities(notes, 'note')}

Generate a clear, professional summary using ONLY the data provided above. 
CRITICAL: Always include Activity Overview section showing the counts above.
If activities exist, include Recent Timeline section.
Do not invent any information. Use the exact format specified in the system prompt."""
        
        try:
            # Call LLM for formatting
            formatted_response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_input=user_prompt
            )
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error formatting lead summary with LLM: {e}", exc_info=True)
            # Fallback to simple formatting
            return self._format_summary_fallback(summary_data)
    
    def _format_timeline_for_llm(self, recent_activity: List[Dict[str, Any]]) -> str:
        """Format recent activity timeline for LLM prompt."""
        if not recent_activity:
            return "No recent activity"
        
        formatted = []
        for activity in recent_activity:
            date = activity.get("date", "N/A")
            activity_type = activity.get("type", "N/A")
            summary = activity.get("summary", "N/A")
            formatted.append(f"- {date} | {activity_type.upper()} | {summary}")
        
        return "\n".join(formatted)
    
    def _format_activities(self, activities: List[Dict[str, Any]], activity_type: str) -> str:
        """Format activities list for LLM prompt."""
        if not activities:
            return "None"
        
        formatted = []
        for activity in activities[:10]:  # Limit to 10 most recent
            if activity_type == "call":
                date = activity.get("created_at", "N/A")
                status = activity.get("status", "N/A")
                direction = activity.get("direction", "N/A")
                formatted.append(f"- {date} | {direction} | Status: {status}")
            elif activity_type == "email":
                date = activity.get("created_at", "N/A")
                subject = activity.get("subject", "N/A")
                to_email = activity.get("to", "N/A")
                formatted.append(f"- {date} | To: {to_email} | Subject: {subject}")
            elif activity_type == "meeting":
                date = activity.get("created_at", "N/A")
                name = activity.get("meeting_name", "N/A")
                location = activity.get("location", "N/A")
                formatted.append(f"- {date} | {name} | Location: {location}")
            elif activity_type == "note":
                date = activity.get("created_at", "N/A")
                content = activity.get("content", "N/A")
                # Truncate long content
                if len(content) > 100:
                    content = content[:100] + "..."
                formatted.append(f"- {date} | {content}")
        
        return "\n".join(formatted) if formatted else "None"
    
    def _format_summary_fallback(self, summary_data: Dict[str, Any]) -> str:
        """Fallback formatting if LLM fails."""
        lead = summary_data.get("lead", {})
        activity_counts = summary_data.get("activity_counts", {})
        
        lead_name = lead.get("name", "Unknown")
        status = lead.get("status", "N/A")
        owner = lead.get("owner", "N/A")
        
        lines = [
            f"Lead: {lead_name}",
            f"Status: {status}",
            f"Owner: {owner}",
            "",
            "Activity Summary:",
            f"- {activity_counts.get('calls', 0)} Calls",
            f"- {activity_counts.get('emails', 0)} Emails",
            f"- {activity_counts.get('meetings', 0)} Meetings",
            f"- {activity_counts.get('notes', 0)} Notes"
        ]
        
        return "\n".join(lines)
