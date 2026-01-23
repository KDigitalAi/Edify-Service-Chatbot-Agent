"""
Optional caching utilities using Redis.
Only active if ENABLE_CACHING is True in settings.
Non-breaking: Falls back gracefully if Redis is unavailable.
"""
from typing import Any, Optional
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

# Global Redis client (initialized only if caching is enabled)
_redis_client = None

def get_redis_client():
    """Get Redis client (lazy initialization, only if caching enabled)."""
    global _redis_client
    
    if not settings.ENABLE_CACHING:
        return None
    
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=2,  # Fast fail if Redis unavailable
                socket_timeout=2
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis caching enabled and connected")
        except ImportError:
            logger.warning("redis package not installed - caching disabled. Install with: pip install redis")
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed - caching disabled: {e}")
            return None
    
    return _redis_client

def get_cached(key: str) -> Optional[Any]:
    """
    Get value from cache (if caching enabled).
    Returns None if not found or caching disabled.
    Non-breaking: Always returns None if caching unavailable.
    """
    if not settings.ENABLE_CACHING:
        return None
    
    client = get_redis_client()
    if not client:
        return None
    
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.debug(f"Cache get failed for key {key}: {e}")
    
    return None

def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set value in cache (if caching enabled).
    Returns True if successful, False otherwise.
    Non-breaking: Silently fails if caching unavailable.
    """
    if not settings.ENABLE_CACHING:
        return False
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        ttl = ttl or settings.CACHE_TTL_SECONDS
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.debug(f"Cache set failed for key {key}: {e}")
        return False

def delete_cached(key: str) -> bool:
    """
    Delete value from cache (if caching enabled).
    Returns True if successful, False otherwise.
    Non-breaking: Silently fails if caching unavailable.
    """
    if not settings.ENABLE_CACHING:
        return False
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache delete failed for key {key}: {e}")
        return False

def _normalize_query(query: str) -> str:
    """
    Normalize query string for consistent cache keys.
    Lowercases, strips whitespace, removes extra spaces.
    """
    if not query:
        return ""
    return " ".join(query.lower().strip().split())

def cache_key_chat_history(session_id: str, limit: int = 20) -> str:
    """
    Generate cache key for chat history.
    Includes session_id and limit for proper cache isolation.
    """
    return f"chat_history:{session_id}:limit:{limit}"

def cache_key_crm_query(query: str, table: str, limit: Optional[int] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> str:
    """
    Generate cache key for CRM query.
    Includes: normalized query, table name, pagination params.
    """
    import hashlib
    normalized_query = _normalize_query(query)
    # Include pagination in key if provided
    pagination_str = ""
    if page is not None and page_size is not None:
        pagination_str = f":page:{page}:size:{page_size}"
    elif limit is not None:
        pagination_str = f":limit:{limit}"
    
    key_string = f"{normalized_query}:{table}{pagination_str}"
    query_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"crm_query:{table}:{query_hash}"

def cache_key_rms_query(query: str, table: str, limit: Optional[int] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> str:
    """
    Generate cache key for RMS query.
    Includes: normalized query, table name, pagination params.
    """
    import hashlib
    normalized_query = _normalize_query(query)
    # Include pagination in key if provided
    pagination_str = ""
    if page is not None and page_size is not None:
        pagination_str = f":page:{page}:size:{page_size}"
    elif limit is not None:
        pagination_str = f":limit:{limit}"
    
    key_string = f"{normalized_query}:{table}{pagination_str}"
    query_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"rms_query:{table}:{query_hash}"

def cache_key_lms_query(query: str, limit: Optional[int] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> str:
    """
    Generate cache key for LMS query.
    Includes: normalized query, pagination params.
    """
    import hashlib
    normalized_query = _normalize_query(query)
    # Include pagination in key if provided
    pagination_str = ""
    if page is not None and page_size is not None:
        pagination_str = f":page:{page}:size:{page_size}"
    elif limit is not None:
        pagination_str = f":limit:{limit}"
    
    key_string = f"{normalized_query}{pagination_str}"
    query_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"lms_query:{query_hash}"

def cache_key_llm_response(query: str, context_hash: str) -> str:
    """Generate cache key for LLM response."""
    import hashlib
    combined = f"{query}:{context_hash}"
    response_hash = hashlib.md5(combined.encode()).hexdigest()
    return f"llm_response:{response_hash}"

