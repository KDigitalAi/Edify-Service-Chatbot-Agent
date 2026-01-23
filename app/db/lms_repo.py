from typing import Any, List, Dict, Optional, Union
from app.db.supabase import get_edify_supabase_client
from app.utils.cache import get_cached, set_cached, cache_key_lms_query
from app.utils.retry import retry_with_backoff
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LMSRepo:
    """
    Repository for LMS data access.
    Reads from Edify LMS tables using Edify Supabase client (read-only).
    Contains NO business logic - only data retrieval.
    """
    
    def __init__(self):
        self.supabase = get_edify_supabase_client()
        self.table = "lms_batches"
    
    def _get_table_columns(self) -> str:
        """
        Returns explicit column list for LMS batches table.
        Maintains identical behavior to select("*") by including all columns.
        Based on common LMS batch table structure, search fields, and typical batch fields.
        """
        # Comprehensive column list for lms_batches table
        # Includes all common fields that would be returned by select("*")
        return "id,name,title,description,instructor,course_name,start_date,end_date,schedule,status,capacity,enrolled,location,venue,time_slot,duration,created_at,updated_at"

    def search_lms(
        self, 
        query: str, 
        page: Optional[int] = None, 
        page_size: Optional[int] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Searches LMS batches data.
        Returns raw verified data from Supabase.
        Optional caching: Uses cache if enabled (non-breaking).
        Optional pagination: If page/page_size provided, returns paginated response.
        
        Args:
            query: Search query string
            page: Optional page number (1-indexed). If provided with page_size, returns paginated response.
            page_size: Optional number of records per page. If provided with page, returns paginated response.
            
        Returns:
            If page/page_size provided: Dict with keys: data, total, page, page_size, has_more
            Otherwise: List of LMS batch records (raw data from Supabase) - DEFAULT BEHAVIOR
        """
        # If pagination params provided, use paginated method
        if page is not None and page_size is not None:
            return self.search_lms_paginated(query, page=page, page_size=page_size)
        
        # DEFAULT BEHAVIOR: No pagination - return List (existing behavior)
        try:
            # READ-THROUGH: Try cache first (non-breaking if cache unavailable)
            cache_key = cache_key_lms_query(query, limit=10)
            if settings.ENABLE_CACHING:
                cached = get_cached(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for LMS query")
                    return cached
            
            # Cache miss: Build query builder and query database
            query_builder = self.supabase.table(self.table)
            
            # Optimize: Use explicit column list instead of select("*") if enabled
            # This improves query performance while maintaining identical behavior
            if settings.ENABLE_QUERY_OPTIMIZATION:
                select_fields = self._get_table_columns()
                query_builder = query_builder.select(select_fields)
            else:
                # Default behavior: use select("*") when optimization disabled
                query_builder = query_builder.select("*")
            
            # Use Supabase ilike for case-insensitive text search
            # Search across common LMS fields
            query_builder = query_builder.or_(f"name.ilike.%{query}%,title.ilike.%{query}%,description.ilike.%{query}%,instructor.ilike.%{query}%,course_name.ilike.%{query}%")
            query_builder = query_builder.limit(10)
            
            # Optional: Retry with exponential backoff if enabled (behind flag, disabled by default)
            if settings.ENABLE_QUERY_RETRY:
                def execute_query():
                    return query_builder.execute()
                
                try:
                    response = retry_with_backoff(
                        execute_query,
                        exceptions=(Exception,)
                    )
                except Exception as retry_error:
                    logger.error(f"Query retry exhausted: {retry_error}")
                    raise retry_error
            else:
                response = query_builder.execute()
            
            data = response.data if response.data else []
            
            # READ-THROUGH: Cache successful read result (TTL: 5 minutes = 300 seconds)
            # Only cache if we got data (successful read)
            if settings.ENABLE_CACHING and data:
                set_cached(cache_key, data, ttl=300)
            
            logger.info(f"Retrieved {len(data)} LMS records")
            return data
            
        except Exception as e:
            logger.error(f"Error searching LMS: {e}", exc_info=True)
            return []
    
    def search_lms_paginated(
        self, 
        query: str, 
        page: int = 1, 
        page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Paginated LMS search (does not change existing search_lms).
        Returns paginated results with metadata.
        
        Args:
            query: Search query string
            page: Page number (1-indexed)
            page_size: Number of records per page (defaults to settings.DEFAULT_PAGE_SIZE)
            
        Returns:
            Dict with keys: data, total, page, page_size, has_more
        """
        from app.core.config import settings
        from app.utils.cache import cache_key_lms_query
        
        if page < 1:
            page = 1
        if page_size is None:
            page_size = settings.DEFAULT_PAGE_SIZE
        if page_size > settings.MAX_PAGE_SIZE:
            page_size = settings.MAX_PAGE_SIZE
        
        offset = (page - 1) * page_size
        
        try:
            logger.info(f"Paginated LMS search - page: {page}, page_size: {page_size}")
            
            # READ-THROUGH: Try cache first (non-breaking if cache unavailable)
            cache_key = cache_key_lms_query(query, page=page, page_size=page_size)
            if settings.ENABLE_CACHING:
                cached = get_cached(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for paginated LMS query, page {page}")
                    return cached
            
            # Cache miss: Build query with pagination
            if settings.ENABLE_QUERY_OPTIMIZATION:
                select_fields = self._get_table_columns()
                query_builder = self.supabase.table(self.table).select(select_fields, count="exact")
            else:
                # Default behavior: use select("*") when optimization disabled
                query_builder = self.supabase.table(self.table).select("*", count="exact")
            
            # Use Supabase ilike for case-insensitive text search
            query_builder = query_builder.or_(f"name.ilike.%{query}%,title.ilike.%{query}%,description.ilike.%{query}%,instructor.ilike.%{query}%,course_name.ilike.%{query}%")
            
            # Apply pagination
            query_builder = query_builder.order("created_at", desc=True)
            
            # Optional: Retry with exponential backoff if enabled (behind flag, disabled by default)
            if settings.ENABLE_QUERY_RETRY:
                def execute_paginated_query():
                    return query_builder.range(offset, offset + page_size - 1).execute()
                
                try:
                    response = retry_with_backoff(
                        execute_paginated_query,
                        exceptions=(Exception,)
                    )
                except Exception as retry_error:
                    logger.error(f"Paginated query retry exhausted: {retry_error}")
                    raise retry_error
            else:
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
            
            logger.info(f"Retrieved {len(data)} LMS records (page {page})")
            return result
            
        except Exception as e:
            logger.error(f"Error in paginated LMS search: {e}", exc_info=True)
            return {
                "data": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False
            }
