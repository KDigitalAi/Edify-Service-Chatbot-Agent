from typing import Any, List, Dict, Optional, Union
from app.db.supabase import get_edify_supabase_client
from app.utils.cache import get_cached, set_cached, cache_key_crm_query
from app.utils.retry import retry_with_backoff
from app.core.config import settings
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class CRMRepo:
    """
    Repository for CRM data access.
    Provides read and write access to ALL Edify CRM tables using Edify Supabase client.
    Supports: campaigns, leads, tasks, trainers, learners, Course, activity, notes,
              batches, learner_batches, batch_lead, emails, email_templates, calls,
              meetings, message_templates, messages
    Provides CRUD operations: Create, Read, Update, Delete for all CRM tables.
    """
    
    # Table configurations with exact field names from Edify Supabase
    TABLE_CONFIGS = {
        "campaigns": {
            "table": "campaigns",
            "search_fields": ["name", "status", "type", "campaign_owner", "phone"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "leads": {
            "table": "leads",
            "search_fields": ["name", "email", "phone", "lead_status", "lead_stage", "opportunity_status", "lead_source", "lead_owner"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "tasks": {
            "table": "tasks",
            "search_fields": ["subject", "priority", "status", "task_type"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "trainers": {
            "table": "trainers",
            "search_fields": ["trainer_name", "trainer_status", "tech_stack", "email", "phone", "location"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "learners": {
            "table": "learners",
            "search_fields": ["name", "email", "phone", "status", "course", "location", "source"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "Course": {
            "table": "Course",  # Note: capital C as per schema
            "search_fields": ["title", "description", "trainer", "duration"],
            "date_field": "createdAt",  # Note: camelCase as per schema
            "order_field": "createdAt"
        },
        "activity": {
            "table": "activity",
            "search_fields": ["activity_name"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "notes": {
            "table": "notes",
            "search_fields": ["content"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "batches": {
            "table": "batches",
            "search_fields": ["batch_name", "batch_status", "location", "stack"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "learner_batches": {
            "table": "learner_batches",
            "search_fields": ["learner_id", "batch_id"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "batch_lead": {
            "table": "batch_lead",
            "search_fields": ["lead_id", "batch_id"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "emails": {
            "table": "emails",
            "search_fields": ["subject"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "email_templates": {
            "table": "email_templates",
            "search_fields": ["name", "subject"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "calls": {
            "table": "calls",
            "search_fields": ["caller_id", "status", "direction"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "meetings": {
            "table": "meetings",
            "search_fields": ["meeting_name", "location"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "message_templates": {
            "table": "message_templates",
            "search_fields": ["name", "content"],
            "date_field": "created_at",
            "order_field": "created_at"
        },
        "messages": {
            "table": "messages",
            "search_fields": ["subject", "content"],
            "date_field": "created_at",
            "order_field": "created_at"
        }
    }
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
    
    def _get_table_columns(self, table_key: str) -> str:
        """
        Returns explicit column list for each CRM table matching Supabase SQL schema exactly.
        """
        column_map = {
            "campaigns": "id,name,status,type,campaign_date,end_date,campaign_owner,phone,course_id,active,amount_spent,description,user_id,created_at,updated_at",
            "leads": "id,name,phone,email,lead_status,lead_stage,opportunity_status,lead_source,lead_owner,fee_quoted,next_follow_up,description,created_at,updated_at",
            "tasks": "id,subject,due_date,priority,status,task_type,lead_id,batch_id,trainer_id,campaign_id,learner_id,created_at,updated_at",
            "trainers": "id,trainer_name,trainer_status,tech_stack,phone,email,location,joining_date,description,created_at,updated_at",
            "learners": "id,name,id_proof,phone,date_of_birth,email,registered_date,location,batch_id,source,description,total_fees,mode_of_installment_payment,fees_paid,instalment1_screenshot,due_amount,due_date,status,user_id,created_at,updated_at,country_code,payment_id,course,batch_ids,course_ids,trainer_ids,auth_user_id",
            "Course": "id,title,description,picture,archived,\"liveLink\",\"modulesOrder\",\"resumeFiles\",\"createdAt\",\"updatedAt\",\"contentLink\",users,trainer,duration,learner_ids",
            "activity": "id,activity_name,lead_id,batch_id,trainer_id,campaign_id,learner_id,created_at,updated_at",
            "notes": "id,content,lead_id,batch_id,trainer_id,campaign_id,learner_id,created_at,updated_at",
            "batches": "id,batch_name,location,slot,trainer_id,batch_status,topic_status,no_of_students,stack,start_date,tentative_end_date,class_mode,stage,comment,timing,batch_stage,mentor,zoom_account,stack_owner,owner,batch_owner,description,user_id,created_at,updated_at,course_id",
            "learner_batches": "id,learner_id,batch_id,created_at,updated_at",
            "batch_lead": "id,lead_id,batch_id,created_at,updated_at",
            "emails": "id,\"to\",\"from\",subject,body,lead_id,created_at,updated_at",
            "email_templates": "id,name,subject,body,template_type,is_active,created_at,updated_at",
            "calls": "id,caller_id,\"to\",status,agent_id,time,direction,answered_seconds,filename,created_at,updated_at",
            "meetings": "id,meeting_name,location,zoom_meeting_id,start_time,end_time,host_id,participants,lead_id,batch_id,user_id,trainer_id,campaign_id,learner_id,main_task_id,created_at,updated_at",
            "message_templates": "id,name,template_type,content,is_active,created_at,updated_at",
            "messages": "id,subject,content,status,message_type,recipient,sent_at,created_at,updated_at"
        }
        return column_map.get(table_key, "*")  # Fallback to * if table not found
    
    def _detect_table_intent(self, query: str) -> Optional[str]:
        """
        Detects which CRM table the user wants to query based on keywords.
        Uses LENIENT matching with synonyms and variations.
        Returns table key or "leads" as default.
        """
        query_lower = query.lower()
        
        # Table detection keywords with comprehensive synonyms (LENIENT matching)
        table_keywords = {
            "campaigns": ["campaign", "campaigns", "marketing campaign", "marketing"],
            "tasks": ["task", "tasks", "todo", "todos", "to-do", "to do"],
            "trainers": ["trainer", "trainers", "instructor", "instructors", "teacher", "teachers"],
            "learners": ["learner", "learners", "student", "students", "trainee", "trainees"],
            "Course": ["course", "courses", "program", "programs", "curriculum", "curricula"],
            "activity": ["activity", "activities", "log", "logs", "event", "events"],
            "notes": ["note", "notes", "comment", "comments", "remark", "remarks"],
            "leads": ["lead", "leads", "prospect", "prospects", "enquiry", "enquiries", 
                     "inquiry", "inquiries", "customer lead", "potential customer"],
            "batches": ["batch", "batches", "cohort", "cohorts", "training batch"],
            "learner_batches": ["learner batch", "learner batches", "batch enrollment", "batch enrollments"],
            "batch_lead": ["batch lead", "batch leads", "batch enquiry", "batch enquiries"],
            "emails": ["email", "emails", "mail", "e-mail", "e-mail"],
            "email_templates": ["email template", "email templates", "email template", "mail template"],
            "calls": ["call", "calls", "phone call", "phone calls", "telephone"],
            "meetings": ["meeting", "meetings", "appointment", "appointments", "schedule"],
            "message_templates": ["message template", "message templates", "sms template"],
            "messages": ["message", "messages", "chat", "sms", "text message"]
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
            # No specific table mentioned, default to leads
            return "leads"
        
        # Return table with highest score
        for table, score in table_scores.items():
            if score == max_score:
                return table
        
        return "leads"  # Default fallback
    
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
            r'\ball\s+(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # "[entity] details/info/data" patterns
            r'(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)\s+(?:details?|information|info|data)',
            # "list [entity]" patterns
            r'list\s+(?:out\s+)?(?:all\s+)?(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # "show [entity]" patterns
            r'show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # "get [entity]" patterns
            r'get\s+(?:all\s+)?(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # "give [entity]" patterns
            r'give\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # "display [entity]" patterns
            r'display\s+(?:all\s+)?(?:the\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)',
            # Just entity name alone (e.g., "leads", "trainers")
            r'^(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)$',
            # "crm [entity]" or "[entity] in crm"
            r'(?:crm\s+)?(?:trainers?|leads?|campaigns?|tasks?|learners?|courses?|activities?|notes?)(?:\s+in\s+crm)?',
            # "crm data" or "crm information"
            r'crm\s+(?:data|information|info)'
        ]
        
        is_list_query = any(re.search(pattern, query_lower) for pattern in list_query_patterns)
        
        # STEP 4: Extract text query ONLY if this is NOT a list query
        # For list queries, we return all records without text filtering
        if not is_list_query:
            text_query = query
            # Remove common query words that don't represent actual search terms
            # This list is comprehensive to catch all variations
            query_words = [
                # Date keywords
                'today', 'yesterday', 'this week', 'new', 'recent',
                # Action verbs
                'show', 'shows', 'display', 'get', 'give', 'list', 'find', 'fetch', 'search',
                'see', 'view', 'tell', 'provide', 'return', 'bring',
                # Pronouns and filler words
                'me', 'my', 'i', 'want', 'need', 'please', 'can', 'could', 'would',
                # System keywords
                'crm', 'data', 'details', 'information', 'info', 'record', 'records',
                # Articles and determiners
                'all', 'the', 'a', 'an', 'some', 'any', 'every', 'each',
                # Verb forms
                's', 'is', 'are', 'was', 'were', 'have', 'has', 'had',
                # Entity names (will be detected separately)
                'campaign', 'campaigns', 'lead', 'leads', 'task', 'tasks',
                'trainer', 'trainers', 'learner', 'learners', 'course', 'courses',
                'activity', 'activities', 'note', 'notes',
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
        Optional optimization: Select specific fields if ENABLE_QUERY_OPTIMIZATION is enabled.
        """
        table_name = table_config["table"]
        search_fields = table_config["search_fields"]
        date_field = table_config["date_field"]
        order_field = table_config["order_field"]
        
        # Optimize: Use explicit column list instead of select("*") if enabled
        # This improves query performance while maintaining identical behavior
        if settings.ENABLE_QUERY_OPTIMIZATION:
            table_key = None
            for key, config in self.TABLE_CONFIGS.items():
                if config["table"] == table_name:
                    table_key = key
                    break
            
            if table_key:
                select_fields = self._get_table_columns(table_key)
                query_builder = self.supabase.table(table_name).select(select_fields)
            else:
                # Fallback to * if table not found in config
                query_builder = self.supabase.table(table_name).select("*")
        else:
            # Default behavior: use select("*") when optimization disabled
            query_builder = self.supabase.table(table_name).select("*")
        
        # Apply date filters if present
        if filters["start_date"] and filters["end_date"]:
            # Format dates for Supabase (ISO format)
            start_iso = filters["start_date"].isoformat()
            end_iso = filters["end_date"].isoformat()
            
            query_builder = query_builder.gte(date_field, start_iso)
            query_builder = query_builder.lte(date_field, end_iso)
            
            logger.info(f"Applied date filter on {date_field}: {start_iso} to {end_iso}")
        
        # STEP 5: Apply filters ONLY when clear and specific
        # Default behavior: return all records if no specific filter
        
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
        # Optional: Retry with exponential backoff if enabled (behind flag, disabled by default)
        if settings.ENABLE_QUERY_RETRY:
            def execute_query():
                return query_builder.limit(limit).execute()
            
            try:
                response = retry_with_backoff(
                    execute_query,
                    exceptions=(Exception,)
                )
            except Exception as retry_error:
                logger.error(f"Query retry exhausted: {retry_error}")
                raise retry_error
        else:
            response = query_builder.limit(limit).execute()
        
        return response.data if response.data else []
    
    def search_crm_paginated(
        self, 
        query: str, 
        page: int = 1, 
        page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        NEW METHOD: Paginated CRM search (does not change existing search_crm).
        Returns paginated results with metadata.
        
        Args:
            query: Search query string
            page: Page number (1-indexed)
            page_size: Number of records per page (defaults to settings.DEFAULT_PAGE_SIZE)
            
        Returns:
            Dict with keys: data, total, page, page_size, has_more
        """
        from app.core.config import settings
        
        if page < 1:
            page = 1
        if page_size is None:
            page_size = settings.DEFAULT_PAGE_SIZE
        if page_size > settings.MAX_PAGE_SIZE:
            page_size = settings.MAX_PAGE_SIZE
        
        offset = (page - 1) * page_size
        
        try:
            # Detect which table to query
            table_key = self._detect_table_intent(query)
            table_config = self.TABLE_CONFIGS[table_key]
            
            logger.info(f"Paginated search - table: {table_key}, page: {page}, page_size: {page_size}")
            
            # READ-THROUGH: Try cache first (non-breaking if cache unavailable)
            cache_key = cache_key_crm_query(query, table_key, page=page, page_size=page_size)
            if settings.ENABLE_CACHING:
                cached = get_cached(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for paginated CRM query: {table_key}, page {page}")
                    return cached
            
            # Cache miss: Parse filters and query database
            filters = self._parse_date_filters(query)
            
            # Build query with pagination
            table_name = table_config["table"]
            search_fields = table_config["search_fields"]
            date_field = table_config["date_field"]
            order_field = table_config["order_field"]
            
            # Optimize: Use explicit column list instead of select("*") if enabled
            if settings.ENABLE_QUERY_OPTIMIZATION:
                select_fields = self._get_table_columns(table_key)
                query_builder = self.supabase.table(table_name).select(select_fields, count="exact")
            else:
                # Default behavior: use select("*") when optimization disabled
                query_builder = self.supabase.table(table_name).select("*", count="exact")
            
            # Apply filters (same logic as _build_query)
            if filters["start_date"] and filters["end_date"]:
                start_iso = filters["start_date"].isoformat()
                end_iso = filters["end_date"].isoformat()
                query_builder = query_builder.gte(date_field, start_iso)
                query_builder = query_builder.lte(date_field, end_iso)
            
            text_query_applied = False
            if filters.get("text_query"):
                text_query = filters["text_query"].strip()
                common_words = {'out', 'the', 'all', 'me', 'my', 'i', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'of', 'for', 'to', 'with'}
                if len(text_query) > 2 and text_query.lower() not in common_words:
                    or_conditions = ",".join([f"{field}.ilike.%{text_query}%" for field in search_fields])
                    query_builder = query_builder.or_(or_conditions)
                    text_query_applied = True
            
            # Apply pagination
            query_builder = query_builder.order(order_field, desc=True)
            response = query_builder.range(offset, offset + page_size - 1).execute()
            
            data = response.data if response.data else []
            total = response.count if hasattr(response, 'count') and response.count is not None else len(data)
            has_more = (offset + page_size) < total
            
            result = {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": has_more
            }
            
            # READ-THROUGH: Cache successful read result (TTL: 5 minutes = 300 seconds)
            # Only cache if we got data (successful read)
            if settings.ENABLE_CACHING and data:
                set_cached(cache_key, result, ttl=300)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in paginated CRM search: {e}", exc_info=True)
            return {
                "data": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False
            }
    
    def search_crm(
        self, 
        query: str, 
        page: Optional[int] = None, 
        page_size: Optional[int] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Searches CRM data across all supported tables.
        Automatically detects which table to query based on user intent.
        Returns raw verified data from Supabase.
        Optional caching: Uses cache if enabled (non-breaking).
        Optional pagination: If page/page_size provided, returns paginated response.
        
        Args:
            query: Search query string (can include table name, date keywords, text search)
            page: Optional page number (1-indexed). If provided with page_size, returns paginated response.
            page_size: Optional number of records per page. If provided with page, returns paginated response.
            
        Returns:
            If page/page_size provided: Dict with keys: data, total, page, page_size, has_more
            Otherwise: List of CRM records (raw data from Supabase) - DEFAULT BEHAVIOR
        """
        # If pagination params provided, use paginated method
        if page is not None and page_size is not None:
            return self.search_crm_paginated(query, page=page, page_size=page_size)
        
        # DEFAULT BEHAVIOR: No pagination - return List (existing behavior)
        try:
            # Detect which table to query
            table_key = self._detect_table_intent(query)
            table_config = self.TABLE_CONFIGS[table_key]
            
            logger.info(f"Detected table: {table_key} (table: {table_config['table']})")
            
            # READ-THROUGH: Try cache first (non-breaking if cache unavailable)
            cache_key = cache_key_crm_query(query, table_key, limit=50)
            if settings.ENABLE_CACHING:
                cached = get_cached(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for CRM query: {table_key}")
                    return cached
            
            # Cache miss: Parse filters and query database
            filters = self._parse_date_filters(query)
            
            # Build and execute query
            data = self._build_query(table_config, filters, limit=50)
            
            # READ-THROUGH: Cache successful read result (TTL: 5 minutes = 300 seconds)
            # Only cache if we got data (successful read)
            if settings.ENABLE_CACHING and data:
                set_cached(cache_key, data, ttl=300)
            
            logger.info(f"Retrieved {len(data)} records from {table_config['table']}")
            return data
            
        except Exception as e:
            logger.error(f"Error searching CRM: {e}", exc_info=True)
            # Try fallback: query leads table with simple text search
            try:
                logger.info("Falling back to leads table with simple text search")
                filters = self._parse_date_filters(query)
                table_config = self.TABLE_CONFIGS["leads"]
                data = self._build_query(table_config, filters, limit=50)
                return data
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}", exc_info=True)
                return []
    
    # ========================================================================
    # CRUD OPERATIONS - CREATE, UPDATE, DELETE
    # ========================================================================
    
    def create_lead(self, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new lead in the CRM system.
        
        Args:
            lead_data: Dictionary containing lead fields (name, email, phone, etc.)
            
        Returns:
            Created lead record if successful, raises Exception on failure
            
        Raises:
            ValueError: If required fields are missing
            Exception: If Supabase insert fails (RLS, permission, constraint, etc.)
        """
        try:
            # Validate required fields (matching SQL schema: name and phone are NOT NULL)
            if not lead_data.get("name"):
                raise ValueError("Name is required")
            if not lead_data.get("phone"):
                raise ValueError("Phone is required")
            
            # Add timestamps
            from datetime import datetime
            lead_data["created_at"] = datetime.now().isoformat()
            lead_data["updated_at"] = datetime.now().isoformat()
            
            # Set default values for required fields if not provided (matching SQL defaults)
            if "lead_status" not in lead_data:
                lead_data["lead_status"] = "Not Contacted"
            if "lead_stage" not in lead_data:
                lead_data["lead_stage"] = "lead"
            if "opportunity_status" not in lead_data:
                lead_data["opportunity_status"] = "Visiting"
            if "description" not in lead_data:
                lead_data["description"] = ""
            
            # Log insert attempt with full payload
            logger.info(f"Attempting to insert lead into Supabase: {lead_data.get('name', 'Unknown')}")
            logger.debug(f"Full lead_data payload: {lead_data}")
            
            result = self.supabase.table("leads").insert(lead_data).execute()
            
            # CRITICAL FORENSIC DEBUGGING: Log complete response
            # Check all possible response attributes
            response_attrs = {
                'data': result.data,
                'error': getattr(result, 'error', None),
                'status_code': getattr(result, 'status_code', None),
                'count': getattr(result, 'count', None),
            }
            
            # Try to get HTTP status from underlying response if available
            try:
                if hasattr(result, '_response'):
                    response_attrs['http_status'] = getattr(result._response, 'status_code', None)
                if hasattr(result, 'response'):
                    response_attrs['http_status'] = getattr(result.response, 'status_code', None)
            except:
                pass
            
            logger.info(f"Supabase insert response - Full details: {response_attrs}")
            logger.info(f"  - result.data type: {type(result.data)}, length: {len(result.data) if isinstance(result.data, list) else 'N/A'}")
            logger.info(f"  - result.error: {response_attrs['error']}")
            logger.info(f"  - HTTP status: {response_attrs.get('http_status', 'unknown')}")
            
            # Check for explicit errors in response
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase insert failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase insert failed: {error_details}"
                logger.error(error_msg)
                logger.error(f"Full error details: {error_details}")
                raise Exception(error_msg)
            
            # Validate result.data exists and is non-empty
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue or constraint violation)"
                logger.error(error_msg)
                logger.error("This usually indicates:")
                logger.error("  1. Row Level Security (RLS) is blocking the insert")
                logger.error("  2. Service role key lacks INSERT permission")
                logger.error("  3. Missing required NOT NULL column")
                logger.error("  4. Constraint violation (unique, foreign key, etc.)")
                raise Exception(error_msg)
            
            if not isinstance(result.data, list):
                error_msg = f"Supabase insert failed: Invalid response data type (expected list, got {type(result.data)})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list (insert was rejected silently)"
                logger.error(error_msg)
                logger.error("Possible causes:")
                logger.error("  - RLS policy blocking insert")
                logger.error("  - Missing required fields")
                logger.error("  - Constraint violation")
                raise Exception(error_msg)
            
            # Validate returned record structure
            created_record = result.data[0]
            if not isinstance(created_record, dict):
                error_msg = f"Supabase insert failed: Invalid record structure (expected dict, got {type(created_record)})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # CRITICAL: Verify record has ID (database confirmation)
            if "id" not in created_record or not created_record.get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID (database inconsistency)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Success - record persisted with valid ID
            logger.info(f"Successfully created lead: {lead_data.get('name', 'Unknown')} (ID: {created_record.get('id')})")
            return created_record
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Log and re-raise all other exceptions (including our validation failures)
            logger.error(f"Error creating lead: {e}", exc_info=True)
            raise
    
    def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing lead.
        
        Args:
            lead_id: ID of the lead to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated lead record if successful, None otherwise
        """
        try:
            # Add updated timestamp
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("leads").update(update_data).eq("id", lead_id).execute()
            if result.data:
                logger.info(f"Updated lead: {lead_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating lead: {e}", exc_info=True)
            return None
    
    def delete_lead(self, lead_id: str) -> bool:
        """
        Delete a lead from the CRM system.
        
        Args:
            lead_id: ID of the lead to delete
            
        Returns:
            True if successful, raises Exception on failure
            
        Raises:
            Exception: If deletion fails (lead not found, RLS, permission, etc.)
        """
        try:
            logger.info(f"Attempting to delete lead ID: {lead_id}")
            
            result = self.supabase.table("leads").delete().eq("id", lead_id).execute()
            
            # CRITICAL FORENSIC DEBUGGING: Log complete response
            response_attrs = {
                'data': result.data,
                'error': getattr(result, 'error', None),
                'status_code': getattr(result, 'status_code', None),
                'count': getattr(result, 'count', None),
            }
            
            # Try to get HTTP status
            try:
                if hasattr(result, '_response'):
                    response_attrs['http_status'] = getattr(result._response, 'status_code', None)
                if hasattr(result, 'response'):
                    response_attrs['http_status'] = getattr(result.response, 'status_code', None)
            except:
                pass
            
            logger.info(f"Supabase delete response - Full details: {response_attrs}")
            logger.info(f"  - result.data type: {type(result.data)}, length: {len(result.data) if isinstance(result.data, list) else 'N/A'}")
            logger.info(f"  - result.error: {response_attrs['error']}")
            logger.info(f"  - HTTP status: {response_attrs.get('http_status', 'unknown')}")
            
            # Check for explicit errors in response
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                logger.error(f"Full error details: {error_details}")
                raise Exception(error_msg)
            
            # CRITICAL: Verify affected rows - result.data must contain deleted record
            if not result.data:
                error_msg = f"Lead not found or deletion failed: No data returned for lead ID {lead_id} (possible RLS/permission issue or lead does not exist)"
                logger.error(error_msg)
                logger.error("This usually indicates:")
                logger.error("  1. Lead with this ID does not exist")
                logger.error("  2. Row Level Security (RLS) is blocking the delete")
                logger.error("  3. Service role key lacks DELETE permission")
                raise Exception(error_msg)
            
            if not isinstance(result.data, list):
                error_msg = f"Supabase delete failed: Invalid response data type (expected list, got {type(result.data)})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if len(result.data) == 0:
                error_msg = f"Lead not found: No record deleted for lead ID {lead_id} (record does not exist or was already deleted)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Success - record deleted (result.data contains the deleted record)
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            deleted_name = deleted_record.get('name', 'Unknown')
            
            # Verify the deleted record ID matches the requested ID
            if str(deleted_id) != str(lead_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({lead_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted lead: {lead_id} (name: {deleted_name})")
            return True
        except Exception as e:
            # Log and re-raise all exceptions (including our validation failures)
            logger.error(f"Error deleting lead: {e}", exc_info=True)
            raise
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new campaign."""
        try:
            from datetime import datetime
            import re
            
            # Normalize date fields if provided
            if "campaign_date" in campaign_data and campaign_data["campaign_date"]:
                campaign_date = campaign_data["campaign_date"]
                if isinstance(campaign_date, str):
                    try:
                        if "/" in campaign_date:
                            parts = campaign_date.split("/")
                            if len(parts) == 3:
                                month, day, year = parts
                                dt = datetime(int(year), int(month), int(day))
                                campaign_data["campaign_date"] = dt.isoformat()
                        elif "-" in campaign_date and len(campaign_date) == 10:
                            if "T" not in campaign_date:
                                campaign_data["campaign_date"] = f"{campaign_date}T00:00:00"
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse campaign_date '{campaign_date}': {e}")
            
            if "end_date" in campaign_data and campaign_data["end_date"]:
                end_date = campaign_data["end_date"]
                if isinstance(end_date, str):
                    try:
                        if "/" in end_date:
                            parts = end_date.split("/")
                            if len(parts) == 3:
                                month, day, year = parts
                                dt = datetime(int(year), int(month), int(day))
                                campaign_data["end_date"] = dt.isoformat()
                        elif "-" in end_date and len(end_date) == 10:
                            if "T" not in end_date:
                                campaign_data["end_date"] = f"{end_date}T00:00:00"
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse end_date '{end_date}': {e}")
            
            campaign_data["created_at"] = datetime.now().isoformat()
            campaign_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("campaigns").insert(campaign_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created campaign: {campaign_data.get('name', 'Unknown')} (ID: {result.data[0].get('id')})")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating campaign: {e}", exc_info=True)
            raise
    
    def update_campaign(self, campaign_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing campaign."""
        try:
            from datetime import datetime
            import re
            
            # Normalize date fields if provided
            if "campaign_date" in update_data and update_data["campaign_date"]:
                campaign_date = update_data["campaign_date"]
                if isinstance(campaign_date, str):
                    try:
                        # Handle formats like "7/2/2026", "07/02/2026", "2026-07-02", etc.
                        if "/" in campaign_date:
                            parts = campaign_date.split("/")
                            if len(parts) == 3:
                                month, day, year = parts
                                dt = datetime(int(year), int(month), int(day))
                                update_data["campaign_date"] = dt.isoformat()
                        elif "-" in campaign_date and len(campaign_date) == 10:
                            if "T" not in campaign_date:
                                update_data["campaign_date"] = f"{campaign_date}T00:00:00"
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse campaign_date '{campaign_date}': {e}")
            
            if "end_date" in update_data and update_data["end_date"]:
                end_date = update_data["end_date"]
                if isinstance(end_date, str):
                    try:
                        if "/" in end_date:
                            parts = end_date.split("/")
                            if len(parts) == 3:
                                month, day, year = parts
                                dt = datetime(int(year), int(month), int(day))
                                update_data["end_date"] = dt.isoformat()
                        elif "-" in end_date and len(end_date) == 10:
                            if "T" not in end_date:
                                update_data["end_date"] = f"{end_date}T00:00:00"
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse end_date '{end_date}': {e}")
            
            # Phone field is accepted and passed through
            # All fields including phone, campaign_date, end_date are now accepted
            
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("campaigns").update(update_data).eq("id", campaign_id).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase update failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase update failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Updated campaign: {campaign_id}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error updating campaign: {e}", exc_info=True)
            raise
    
    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign from the CRM system."""
        try:
            logger.info(f"Attempting to delete campaign ID: {campaign_id}")
            
            result = self.supabase.table("campaigns").delete().eq("id", campaign_id).execute()
            
            # Validate result
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Campaign not found or deletion failed: No data returned for campaign ID {campaign_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Campaign not found: No record deleted for campaign ID {campaign_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(campaign_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({campaign_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted campaign: {campaign_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting campaign: {e}", exc_info=True)
            raise
    
    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new task."""
        try:
            from datetime import datetime
            task_data["created_at"] = datetime.now().isoformat()
            task_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("tasks").insert(task_data).execute()
            if result.data:
                logger.info(f"Created task: {task_data.get('subject', 'Unknown')}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return None
    
    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing task."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("tasks").update(update_data).eq("id", task_id).execute()
            if result.data:
                logger.info(f"Updated task: {task_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating task: {e}", exc_info=True)
            return None
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the CRM system."""
        try:
            logger.info(f"Attempting to delete task ID: {task_id}")
            
            result = self.supabase.table("tasks").delete().eq("id", task_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Task not found or deletion failed: No data returned for task ID {task_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Task not found: No record deleted for task ID {task_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(task_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({task_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}", exc_info=True)
            raise
    
    def create_trainer(self, trainer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new trainer."""
        try:
            from datetime import datetime
            trainer_data["created_at"] = datetime.now().isoformat()
            trainer_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("trainers").insert(trainer_data).execute()
            if result.data:
                logger.info(f"Created trainer: {trainer_data.get('trainer_name', 'Unknown')}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating trainer: {e}", exc_info=True)
            return None
    
    def update_trainer(self, trainer_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing trainer."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("trainers").update(update_data).eq("id", trainer_id).execute()
            if result.data:
                logger.info(f"Updated trainer: {trainer_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating trainer: {e}", exc_info=True)
            return None
    
    def delete_trainer(self, trainer_id: str) -> bool:
        """Delete a trainer from the CRM system."""
        try:
            logger.info(f"Attempting to delete trainer ID: {trainer_id}")
            
            result = self.supabase.table("trainers").delete().eq("id", trainer_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Trainer not found or deletion failed: No data returned for trainer ID {trainer_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Trainer not found: No record deleted for trainer ID {trainer_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(trainer_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({trainer_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted trainer: {trainer_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting trainer: {e}", exc_info=True)
            raise
    
    def create_learner(self, learner_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new learner."""
        try:
            from datetime import datetime
            learner_data["created_at"] = datetime.now().isoformat()
            learner_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("learners").insert(learner_data).execute()
            if result.data:
                logger.info(f"Created learner: {learner_data.get('name', 'Unknown')}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating learner: {e}", exc_info=True)
            return None
    
    def update_learner(self, learner_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing learner."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("learners").update(update_data).eq("id", learner_id).execute()
            if result.data:
                logger.info(f"Updated learner: {learner_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating learner: {e}", exc_info=True)
            return None
    
    def delete_learner(self, learner_id: str) -> bool:
        """Delete a learner from the CRM system."""
        try:
            logger.info(f"Attempting to delete learner ID: {learner_id}")
            
            result = self.supabase.table("learners").delete().eq("id", learner_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Learner not found or deletion failed: No data returned for learner ID {learner_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Learner not found: No record deleted for learner ID {learner_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(learner_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({learner_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted learner: {learner_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting learner: {e}", exc_info=True)
            raise
    
    def create_course(self, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new course (Course table with capital C)."""
        try:
            from datetime import datetime
            course_data["createdAt"] = datetime.now().isoformat()
            course_data["updatedAt"] = datetime.now().isoformat()
            
            result = self.supabase.table("Course").insert(course_data).execute()
            if result.data:
                logger.info(f"Created course: {course_data.get('title', 'Unknown')}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating course: {e}", exc_info=True)
            return None
    
    def update_course(self, course_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing course."""
        try:
            from datetime import datetime
            update_data["updatedAt"] = datetime.now().isoformat()
            
            result = self.supabase.table("Course").update(update_data).eq("id", course_id).execute()
            if result.data:
                logger.info(f"Updated course: {course_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating course: {e}", exc_info=True)
            return None
    
    def delete_course(self, course_id: str) -> bool:
        """Delete a course from the CRM system."""
        try:
            logger.info(f"Attempting to delete course ID: {course_id}")
            
            result = self.supabase.table("Course").delete().eq("id", course_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Course not found or deletion failed: No data returned for course ID {course_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Course not found: No record deleted for course ID {course_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(course_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({course_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted course: {course_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting course: {e}", exc_info=True)
            raise
    
    def create_activity(self, activity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new activity."""
        try:
            from datetime import datetime
            activity_data["created_at"] = datetime.now().isoformat()
            activity_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("activity").insert(activity_data).execute()
            if result.data:
                logger.info(f"Created activity: {activity_data.get('activity_name', 'Unknown')}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating activity: {e}", exc_info=True)
            return None
    
    def update_activity(self, activity_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing activity."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("activity").update(update_data).eq("id", activity_id).execute()
            if result.data:
                logger.info(f"Updated activity: {activity_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating activity: {e}", exc_info=True)
            return None
    
    def delete_activity(self, activity_id: str) -> bool:
        """Delete an activity from the CRM system."""
        try:
            logger.info(f"Attempting to delete activity ID: {activity_id}")
            
            result = self.supabase.table("activity").delete().eq("id", activity_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Activity not found or deletion failed: No data returned for activity ID {activity_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Activity not found: No record deleted for activity ID {activity_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(activity_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({activity_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted activity: {activity_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting activity: {e}", exc_info=True)
            raise
    
    def create_note(self, note_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new note."""
        try:
            from datetime import datetime
            note_data["created_at"] = datetime.now().isoformat()
            note_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("notes").insert(note_data).execute()
            if result.data:
                logger.info(f"Created note")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating note: {e}", exc_info=True)
            return None
    
    def update_note(self, note_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing note."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("notes").update(update_data).eq("id", note_id).execute()
            if result.data:
                logger.info(f"Updated note: {note_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating note: {e}", exc_info=True)
            return None
    
    def delete_note(self, note_id: str) -> bool:
        """Delete a note from the CRM system."""
        try:
            logger.info(f"Attempting to delete note ID: {note_id}")
            
            result = self.supabase.table("notes").delete().eq("id", note_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Note not found or deletion failed: No data returned for note ID {note_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Note not found: No record deleted for note ID {note_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(note_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({note_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted note: {note_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting note: {e}", exc_info=True)
            raise
    
    # ========================================================================
    # NEW CRM TABLES - CRUD OPERATIONS
    # ========================================================================
    
    def create_batch(self, batch_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new batch."""
        try:
            from datetime import datetime
            batch_data["created_at"] = datetime.now().isoformat()
            batch_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("batches").insert(batch_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created batch: {batch_data.get('name', batch_data.get('batch_name', 'Unknown'))}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating batch: {e}", exc_info=True)
            raise
    
    def update_batch(self, batch_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing batch."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("batches").update(update_data).eq("id", batch_id).execute()
            if result.data:
                logger.info(f"Updated batch: {batch_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating batch: {e}", exc_info=True)
            return None
    
    def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch from the CRM system."""
        try:
            logger.info(f"Attempting to delete batch ID: {batch_id}")
            
            result = self.supabase.table("batches").delete().eq("id", batch_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Batch not found or deletion failed: No data returned for batch ID {batch_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Batch not found: No record deleted for batch ID {batch_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(batch_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({batch_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted batch: {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting batch: {e}", exc_info=True)
            raise
    
    def create_email(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new email record."""
        try:
            from datetime import datetime
            email_data["created_at"] = datetime.now().isoformat()
            email_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("emails").insert(email_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created email: {email_data.get('subject', 'Unknown')}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating email: {e}", exc_info=True)
            raise
    
    def update_email(self, email_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing email record."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("emails").update(update_data).eq("id", email_id).execute()
            if result.data:
                logger.info(f"Updated email: {email_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating email: {e}", exc_info=True)
            return None
    
    def delete_email(self, email_id: str) -> bool:
        """Delete an email record from the CRM system."""
        try:
            logger.info(f"Attempting to delete email ID: {email_id}")
            
            result = self.supabase.table("emails").delete().eq("id", email_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Email not found or deletion failed: No data returned for email ID {email_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Email not found: No record deleted for email ID {email_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(email_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({email_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted email: {email_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting email: {e}", exc_info=True)
            raise
    
    def create_call(self, call_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new call record."""
        try:
            from datetime import datetime
            call_data["created_at"] = datetime.now().isoformat()
            call_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("calls").insert(call_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created call: {call_data.get('subject', call_data.get('phone_number', 'Unknown'))}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating call: {e}", exc_info=True)
            raise
    
    def update_call(self, call_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing call record."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("calls").update(update_data).eq("id", call_id).execute()
            if result.data:
                logger.info(f"Updated call: {call_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating call: {e}", exc_info=True)
            return None
    
    def delete_call(self, call_id: str) -> bool:
        """Delete a call record from the CRM system."""
        try:
            logger.info(f"Attempting to delete call ID: {call_id}")
            
            result = self.supabase.table("calls").delete().eq("id", call_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Call not found or deletion failed: No data returned for call ID {call_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Call not found: No record deleted for call ID {call_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(call_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({call_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted call: {call_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting call: {e}", exc_info=True)
            raise
    
    def create_meeting(self, meeting_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new meeting record."""
        try:
            from datetime import datetime
            meeting_data["created_at"] = datetime.now().isoformat()
            meeting_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("meetings").insert(meeting_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created meeting: {meeting_data.get('title', 'Unknown')}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating meeting: {e}", exc_info=True)
            raise
    
    def update_meeting(self, meeting_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing meeting record."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("meetings").update(update_data).eq("id", meeting_id).execute()
            if result.data:
                logger.info(f"Updated meeting: {meeting_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating meeting: {e}", exc_info=True)
            return None
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting record from the CRM system."""
        try:
            logger.info(f"Attempting to delete meeting ID: {meeting_id}")
            
            result = self.supabase.table("meetings").delete().eq("id", meeting_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Meeting not found or deletion failed: No data returned for meeting ID {meeting_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Meeting not found: No record deleted for meeting ID {meeting_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(meeting_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({meeting_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted meeting: {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting meeting: {e}", exc_info=True)
            raise
    
    def create_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new message record."""
        try:
            from datetime import datetime
            message_data["created_at"] = datetime.now().isoformat()
            message_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("messages").insert(message_data).execute()
            
            # Validate result
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created message: {message_data.get('subject', message_data.get('content', 'Unknown')[:50])}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating message: {e}", exc_info=True)
            raise
    
    def update_message(self, message_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing message record."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("messages").update(update_data).eq("id", message_id).execute()
            if result.data:
                logger.info(f"Updated message: {message_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating message: {e}", exc_info=True)
            return None
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message record from the CRM system."""
        try:
            logger.info(f"Attempting to delete message ID: {message_id}")
            
            result = self.supabase.table("messages").delete().eq("id", message_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Message not found or deletion failed: No data returned for message ID {message_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Message not found: No record deleted for message ID {message_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(message_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({message_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted message: {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting message: {e}", exc_info=True)
            raise
    
    # ========================================================================
    # JOIN/LOOKUP TABLES - CRUD OPERATIONS
    # ========================================================================
    
    def create_batch_lead(self, batch_lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new batch_lead relationship."""
        try:
            from datetime import datetime
            batch_lead_data["created_at"] = datetime.now().isoformat()
            batch_lead_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("batch_lead").insert(batch_lead_data).execute()
            
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created batch_lead relationship")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating batch_lead: {e}", exc_info=True)
            raise
    
    def update_batch_lead(self, batch_lead_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing batch_lead relationship."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("batch_lead").update(update_data).eq("id", batch_lead_id).execute()
            if result.data:
                logger.info(f"Updated batch_lead: {batch_lead_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating batch_lead: {e}", exc_info=True)
            return None
    
    def delete_batch_lead(self, batch_lead_id: str) -> bool:
        """Delete a batch_lead relationship from the CRM system."""
        try:
            logger.info(f"Attempting to delete batch_lead ID: {batch_lead_id}")
            
            result = self.supabase.table("batch_lead").delete().eq("id", batch_lead_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Batch_lead not found or deletion failed: No data returned for batch_lead ID {batch_lead_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Batch_lead not found: No record deleted for batch_lead ID {batch_lead_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(batch_lead_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({batch_lead_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted batch_lead: {batch_lead_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting batch_lead: {e}", exc_info=True)
            raise
    
    def create_learner_batch(self, learner_batch_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new learner_batches relationship."""
        try:
            from datetime import datetime
            learner_batch_data["created_at"] = datetime.now().isoformat()
            learner_batch_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("learner_batches").insert(learner_batch_data).execute()
            
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created learner_batches relationship")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating learner_batch: {e}", exc_info=True)
            raise
    
    def update_learner_batch(self, learner_batch_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing learner_batches relationship."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("learner_batches").update(update_data).eq("id", learner_batch_id).execute()
            if result.data:
                logger.info(f"Updated learner_batch: {learner_batch_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating learner_batch: {e}", exc_info=True)
            return None
    
    def delete_learner_batch(self, learner_batch_id: str) -> bool:
        """Delete a learner_batches relationship from the CRM system."""
        try:
            logger.info(f"Attempting to delete learner_batch ID: {learner_batch_id}")
            
            result = self.supabase.table("learner_batches").delete().eq("id", learner_batch_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Learner_batch not found or deletion failed: No data returned for learner_batch ID {learner_batch_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Learner_batch not found: No record deleted for learner_batch ID {learner_batch_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(learner_batch_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({learner_batch_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted learner_batch: {learner_batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting learner_batch: {e}", exc_info=True)
            raise
    
    def create_email_template(self, email_template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new email template."""
        try:
            from datetime import datetime
            email_template_data["created_at"] = datetime.now().isoformat()
            email_template_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_templates").insert(email_template_data).execute()
            
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created email_template: {email_template_data.get('name', 'Unknown')}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating email_template: {e}", exc_info=True)
            raise
    
    def update_email_template(self, email_template_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing email template."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("email_templates").update(update_data).eq("id", email_template_id).execute()
            if result.data:
                logger.info(f"Updated email_template: {email_template_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating email_template: {e}", exc_info=True)
            return None
    
    def delete_email_template(self, email_template_id: str) -> bool:
        """Delete an email template from the CRM system."""
        try:
            logger.info(f"Attempting to delete email_template ID: {email_template_id}")
            
            result = self.supabase.table("email_templates").delete().eq("id", email_template_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Email_template not found or deletion failed: No data returned for email_template ID {email_template_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Email_template not found: No record deleted for email_template ID {email_template_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(email_template_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({email_template_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted email_template: {email_template_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting email_template: {e}", exc_info=True)
            raise
    
    def create_message_template(self, message_template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new message template."""
        try:
            from datetime import datetime
            message_template_data["created_at"] = datetime.now().isoformat()
            message_template_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("message_templates").insert(message_template_data).execute()
            
            if not result.data:
                error_msg = "Supabase insert failed: Empty response data (possible RLS/permission issue)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = "Supabase insert failed: Empty result.data list"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if "id" not in result.data[0] or not result.data[0].get("id"):
                error_msg = "Supabase insert failed: Record created but missing ID"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Created message_template: {message_template_data.get('name', 'Unknown')}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating message_template: {e}", exc_info=True)
            raise
    
    def update_message_template(self, message_template_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing message template."""
        try:
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("message_templates").update(update_data).eq("id", message_template_id).execute()
            if result.data:
                logger.info(f"Updated message_template: {message_template_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating message_template: {e}", exc_info=True)
            return None
    
    def delete_message_template(self, message_template_id: str) -> bool:
        """Delete a message template from the CRM system."""
        try:
            logger.info(f"Attempting to delete message_template ID: {message_template_id}")
            
            result = self.supabase.table("message_templates").delete().eq("id", message_template_id).execute()
            
            if hasattr(result, 'error') and result.error:
                error_details = result.error
                if isinstance(error_details, dict):
                    error_msg = f"Supabase delete failed: {error_details.get('message', error_details)} (code: {error_details.get('code', 'unknown')})"
                else:
                    error_msg = f"Supabase delete failed: {error_details}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not result.data:
                error_msg = f"Message_template not found or deletion failed: No data returned for message_template ID {message_template_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if not isinstance(result.data, list) or len(result.data) == 0:
                error_msg = f"Message_template not found: No record deleted for message_template ID {message_template_id}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            deleted_record = result.data[0]
            deleted_id = deleted_record.get('id')
            
            if str(deleted_id) != str(message_template_id):
                error_msg = f"Delete verification failed: Deleted record ID ({deleted_id}) does not match requested ID ({message_template_id})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Successfully deleted message_template: {message_template_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting message_template: {e}", exc_info=True)
            raise
