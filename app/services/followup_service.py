"""
Follow-up Service for Smart Follow-Up Reminder Generator
Handles retrieval of leads requiring follow-up.
"""

from typing import List, Dict, Any
from app.db.supabase import get_edify_supabase_client
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class FollowUpService:
    """
    Service for managing follow-up reminders.
    Queries leads table to find leads requiring follow-up.
    """
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
        self.table = "leads"
    
    def get_leads_requiring_followup(self) -> List[Dict[str, Any]]:
        """
        Get leads that require follow-up today.
        
        Criteria:
        - next_follow_up <= NOW()
        - lead_status NOT IN ('Closed', 'Lost')
        
        Returns:
            List of lead dictionaries with required fields
        """
        try:
            # Get current datetime in ISO format for comparison
            now = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Querying leads requiring follow-up (next_follow_up <= {now})")
            
            # Build query: leads where next_follow_up <= now AND status not closed/lost
            query = (
                self.supabase.table(self.table)
                .select("id,name,phone,email,lead_status,next_follow_up,lead_owner,updated_at")
                .lte("next_follow_up", now)  # next_follow_up <= now
                .not_.in_("lead_status", ["Closed", "Lost"])  # Exclude closed/lost leads
                .order("next_follow_up", desc=False)  # Order by next_follow_up ASC (oldest first)
            )
            
            response = query.execute()
            
            leads = response.data if response.data else []
            
            # Filter out leads with null next_follow_up (safety check)
            valid_leads = [
                lead for lead in leads 
                if lead.get("next_follow_up") is not None
            ]
            
            logger.info(f"Found {len(valid_leads)} leads requiring follow-up")
            
            return valid_leads
            
        except Exception as e:
            logger.error(f"Error fetching leads requiring follow-up: {e}", exc_info=True)
            # Return empty list on error to prevent breaking the flow
            return []

