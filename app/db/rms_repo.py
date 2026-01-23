from typing import Any, List, Dict, Optional
from app.db.supabase import get_edify_supabase_client
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class RMSRepo:
    """
    Repository for RMS data access.
    Reads from ALL Edify RMS tables using Edify Supabase client (read-only).
    Supports: job_openings, candidates, companies, interviews, tasks
    Contains NO business logic - only data retrieval.
    """
    
    # Table configurations with exact field names from Edify RMS schema
    TABLE_CONFIGS = {
        "job_openings": {
            "table": "job_openings",
            "search_fields": ["job_title", "job_type", "industry", "department", "city", "country", "state", "job_status", "location"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "candidates": {
            "table": "candidates",
            "search_fields": ["candidate_name", "job_title", "industry", "email", "mobile", "department_name", "city", "country", "state", "candidate_status", "current_job_title"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "companies": {
            "table": "companies",
            "search_fields": ["company_name", "email", "phone", "city", "country", "state", "status", "vendor_name"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "interviews": {
            "table": "interviews",
            "search_fields": ["job_title", "interview_name", "interview_type", "interview_owner", "location", "status", "interview_status"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "tasks": {
            "table": "tasks",
            "search_fields": ["subject", "priority", "status", "task_type"],
            "date_field": "created_at",
            "order_field": "created_at"
        }
    }
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
    
    def _detect_table_intent(self, query: str) -> Optional[str]:
        """
        Detects which RMS table the user wants to query based on keywords.
        Uses LENIENT matching with synonyms and variations.
        Returns table key or "candidates" as default.
        """
        query_lower = query.lower()
        
        # Table detection keywords with comprehensive synonyms (LENIENT matching)
        table_keywords = {
            "job_openings": ["job opening", "job openings", "opening", "openings", "position", "positions", 
                           "vacancy", "vacancies", "job", "jobs", "role", "roles", "hiring", "recruitment"],
            "candidates": ["candidate", "candidates", "applicant", "applicants", "prospect", "prospects"],
            "companies": ["company", "companies", "organization", "organizations", "org", "orgs", 
                         "employer", "employers", "client", "clients"],
            "interviews": ["interview", "interviews", "screening", "screenings", "meeting", "meetings"],
            "tasks": ["task", "tasks", "todo", "todos", "to-do", "to do", "assignment", "assignments"]
        }
        
        # Count matches for each table
        table_scores = {table: 0 for table in self.TABLE_CONFIGS.keys()}
        
        for table, keywords in table_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', query_lower):
                    table_scores[table] += 1
        
        # Find table with highest score
        max_score = max(table_scores.values())
        if max_score == 0:
            # No specific table mentioned, default to candidates
            return "candidates"
        
        # Return table with highest score
        for table, score in table_scores.items():
            if score == max_score:
                return table
        
        return "candidates"  # Default fallback
    
    def _parse_date_filters(self, query: str) -> Dict[str, Any]:
        """
        Parses date-related keywords from the query string.
        Returns a dict with date filter information.
        """
        query_lower = query.lower()
        filters = {
            "start_date": None,
            "end_date": None,
            "is_new": False,
            "text_query": None
        }
        
        # Get today's date range (start and end of day)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Check for "today" keyword
        if re.search(r'\btoday\b', query_lower):
            filters["start_date"] = today_start
            filters["end_date"] = today_end
        
        # Check for "yesterday" keyword
        elif re.search(r'\byesterday\b', query_lower):
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_end - timedelta(days=1)
            filters["start_date"] = yesterday_start
            filters["end_date"] = yesterday_end
        
        # Check for "this week" keyword
        elif re.search(r'\bthis week\b', query_lower):
            days_since_monday = datetime.now().weekday()
            week_start = today_start - timedelta(days=days_since_monday)
            filters["start_date"] = week_start
            filters["end_date"] = today_end
        
        # Check for "new" keyword (typically means recent, e.g., last 7 days)
        if re.search(r'\bnew\b', query_lower):
            filters["is_new"] = True
            # If no other date filter, default "new" to last 7 days
            if filters["start_date"] is None:
                filters["start_date"] = today_start - timedelta(days=7)
                filters["end_date"] = today_end
        
        # STEP 3: Detect if this is a LIST/GET/SHOW query (should return all records)
        # Patterns that indicate "get all" intent (LENIENT matching)
        list_query_patterns = [
            # "all [entity]" patterns
            r'\ball\s+(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # "[entity] details/info/data" patterns
            r'(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)\s+(?:details?|information|info|data)',
            # "list [entity]" patterns
            r'list\s+(?:out\s+)?(?:all\s+)?(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # "show [entity]" patterns
            r'show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # "get [entity]" patterns
            r'get\s+(?:all\s+)?(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # "give [entity]" patterns
            r'give\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # "display [entity]" patterns
            r'display\s+(?:all\s+)?(?:the\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)',
            # Just entity name alone (e.g., "candidates", "job openings")
            r'^(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)$',
            # "rms [entity]" or "[entity] in rms"
            r'(?:rms\s+)?(?:job\s+openings?|candidates?|companies?|interviews?|tasks?|positions?|roles?)(?:\s+in\s+rms)?',
            # "rms data" or "rms information"
            r'rms\s+(?:data|information|info)'
        ]
        
        is_list_query = any(re.search(pattern, query_lower) for pattern in list_query_patterns)
        
        # STEP 4: Extract text query ONLY if this is NOT a list query
        # For list queries, we return all records without text filtering
        if not is_list_query:
            text_query = query
            # Remove common query words that don't represent actual search terms
            query_words = [
                # Date keywords
                'today', 'yesterday', 'this week', 'new', 'recent',
                # Action verbs
                'show', 'shows', 'display', 'get', 'give', 'list', 'find', 'fetch', 'search',
                'see', 'view', 'tell', 'provide', 'return', 'bring',
                # Pronouns and filler words
                'me', 'my', 'i', 'want', 'need', 'please', 'can', 'could', 'would',
                # System keywords
                'rms', 'data', 'details', 'information', 'info', 'record', 'records',
                # Articles and determiners
                'all', 'the', 'a', 'an', 'some', 'any', 'every', 'each',
                # Verb forms
                's', 'is', 'are', 'was', 'were', 'have', 'has', 'had',
                # Entity names (will be detected separately)
                'job', 'jobs', 'opening', 'openings', 'candidate', 'candidates',
                'company', 'companies', 'interview', 'interviews', 'task', 'tasks',
                'position', 'positions', 'role', 'roles',
                # Common connectors
                'out', 'of', 'in', 'from', 'with', 'for', 'to'
            ]
            for keyword in query_words:
                text_query = re.sub(rf'\b{keyword}\b', '', text_query, flags=re.IGNORECASE)
            text_query = ' '.join(text_query.split())  # Clean up extra spaces
            
            # Only use as text query if there's meaningful content left (more than 2 chars)
            if text_query.strip() and len(text_query.strip()) > 2:
                filters["text_query"] = text_query.strip()
        
        return filters
    
    def _build_query(self, table_config: Dict[str, Any], filters: Dict[str, Any], limit: int = 50):
        """
        Builds and executes Supabase query based on table config and filters.
        """
        table_name = table_config["table"]
        search_fields = table_config["search_fields"]
        date_field = table_config["date_field"]
        order_field = table_config["order_field"]
        
        query_builder = self.supabase.table(table_name).select("*")
        
        # Apply date filters if present
        if filters["start_date"] and filters["end_date"]:
            # Format dates for Supabase (ISO format)
            start_iso = filters["start_date"].isoformat()
            end_iso = filters["end_date"].isoformat()
            
            query_builder = query_builder.gte(date_field, start_iso)
            query_builder = query_builder.lte(date_field, end_iso)
            
            logger.info(f"Applied date filter on {date_field}: {start_iso} to {end_iso}")
        
        # Apply text search ONLY if there's a meaningful text query (not a list query)
        text_query_applied = False
        if filters.get("text_query"):
            # Validate text query is meaningful (not just leftover words)
            text_query = filters["text_query"].strip()
            # Only apply if it's longer than 2 chars and not a common word
            common_words = {'out', 'the', 'all', 'me', 'my', 'i', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'of', 'for', 'to', 'with'}
            if len(text_query) > 2 and text_query.lower() not in common_words:
                # Build OR condition for all search fields
                or_conditions = ",".join([f"{field}.ilike.%{text_query}%" for field in search_fields])
                query_builder = query_builder.or_(or_conditions)
                logger.info(f"Applied text search: {text_query}")
                text_query_applied = True
            else:
                logger.info(f"Ignoring ambiguous text query: '{text_query}' - treating as list query")
                # Clear the text query so we return all records
                filters["text_query"] = None
        
        # If no date filter and no valid text query, return all records (DEFAULT BEHAVIOR)
        if not (filters["start_date"] and filters["end_date"]) and not text_query_applied:
            logger.info("No specific search criteria - returning all records (default behavior)")
        
        # Always order by order_field descending (newest first)
        query_builder = query_builder.order(order_field, desc=True)
        
        # Apply limit
        response = query_builder.limit(limit).execute()
        
        return response.data if response.data else []
    
    def search_rms(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches RMS data across all supported tables.
        Automatically detects which table to query based on user intent.
        Returns raw verified data from Supabase.
        
        Args:
            query: Search query string (can include table name, date keywords, text search)
            
        Returns:
            List of RMS records (raw data from Supabase)
        """
        try:
            # Detect which table to query
            table_key = self._detect_table_intent(query)
            table_config = self.TABLE_CONFIGS[table_key]
            
            logger.info(f"Detected RMS table: {table_key} (table: {table_config['table']})")
            
            # Parse filters
            filters = self._parse_date_filters(query)
            
            # Build and execute query
            data = self._build_query(table_config, filters, limit=50)
            
            logger.info(f"Retrieved {len(data)} records from {table_config['table']}")
            return data
            
        except Exception as e:
            logger.error(f"Error searching RMS: {e}", exc_info=True)
            # Try fallback: query candidates table with simple text search
            try:
                logger.info("Falling back to candidates table with simple text search")
                filters = self._parse_date_filters(query)
                table_config = self.TABLE_CONFIGS["candidates"]
                data = self._build_query(table_config, filters, limit=50)
                return data
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}", exc_info=True)
                return []
    
    def get_all_job_openings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all job openings."""
        return self._get_all_from_table("job_openings", limit)
    
    def get_all_candidates(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all candidates."""
        return self._get_all_from_table("candidates", limit)
    
    def get_all_companies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all companies."""
        return self._get_all_from_table("companies", limit)
    
    def get_all_interviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all interviews."""
        return self._get_all_from_table("interviews", limit)
    
    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return self._get_all_from_table("tasks", limit)
    
    def _get_all_from_table(self, table_key: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Internal method to get all records from a specific table."""
        try:
            table_config = self.TABLE_CONFIGS[table_key]
            filters = {"start_date": None, "end_date": None, "is_new": False, "text_query": None}
            return self._build_query(table_config, filters, limit)
        except Exception as e:
            logger.error(f"Error getting all from {table_key}: {e}", exc_info=True)
            return []
