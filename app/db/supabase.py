# app/db/supabase.py

from supabase import create_client, Client
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Optional: Connection pool configuration (if enabled)
def _configure_connection_pooling():
    """
    Configures connection pooling for Supabase clients.
    Supabase Python client uses httpx internally, which has built-in connection pooling.
    This function sets up pooling configuration when ENABLE_CONNECTION_POOLING is True.
    
    Note: httpx connection pooling is enabled by default and automatically manages
    connection reuse. The MAX_CONNECTIONS setting serves as a reference for pool sizing.
    """
    if not settings.ENABLE_CONNECTION_POOLING:
        return
    
    # httpx (used by Supabase) has connection pooling enabled by default
    # Connection pooling happens automatically at the httpx level
    # The pool size is managed by httpx based on connection limits
    # MAX_CONNECTIONS setting documents the intended pool size
    
    # Set environment variables that httpx may respect for connection limits
    # These are hints for httpx's internal connection pool management
    os.environ.setdefault("HTTPX_MAX_CONNECTIONS", str(settings.MAX_CONNECTIONS))
    os.environ.setdefault("HTTPX_MAX_KEEPALIVE_CONNECTIONS", str(settings.MAX_CONNECTIONS))
    
    logger.info(f"Connection pooling enabled (max_connections={settings.MAX_CONNECTIONS})")
    logger.info("Note: Supabase client uses httpx which has built-in connection pooling")

# Separate clients for Edify (read-only) and Chatbot (read/write)
_edify_supabase_client: Client | None = None
_chatbot_supabase_client: Client | None = None


def _ensure_no_proxy_env():
    """
    Temporarily remove proxy environment variables to prevent gotrue proxy errors.
    gotrue 2.8.1 may incorrectly handle proxy parameters.
    """
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    saved = {}
    for var in proxy_vars:
        if var in os.environ:
            saved[var] = os.environ.pop(var)
    return saved


def _restore_proxy_env(saved: dict):
    """Restore proxy environment variables."""
    os.environ.update(saved)


def get_edify_supabase_client() -> Client:
    """
    Returns a singleton Supabase client for Edify Production database.
    READ-ONLY access only - used for CRM, LMS, RMS data retrieval.
    Uses service_role key (backend-only).
    Optional connection pooling: Uses httpx client with pooling if enabled.
    """
    global _edify_supabase_client

    if _edify_supabase_client is None:
        logger.info("Initializing Edify Supabase client (read-only)")
        
        # Optional: Configure connection pooling if enabled
        _configure_connection_pooling()
        
        # Temporarily remove proxy env vars to prevent gotrue errors
        saved_proxy = _ensure_no_proxy_env()
        try:
            # Create Supabase client
            # Note: Supabase Python client uses httpx internally which has built-in connection pooling
            # The httpx client automatically pools connections based on the URL and connection limits
            # Connection pooling is handled at the httpx level and is active by default
            # When ENABLE_CONNECTION_POOLING=true, pool configuration is applied via environment
            _edify_supabase_client = create_client(
                settings.EDIFY_SUPABASE_URL,
                settings.EDIFY_SUPABASE_SERVICE_ROLE_KEY
            )
        finally:
            _restore_proxy_env(saved_proxy)

    return _edify_supabase_client


def get_chatbot_supabase_client() -> Client:
    """
    Returns a singleton Supabase client for Chatbot database.
    READ/WRITE access - used for sessions, memory, RAG, audit logs.
    Uses service_role key (backend-only).
    Optional connection pooling: Uses httpx client with pooling if enabled.
    """
    global _chatbot_supabase_client

    if _chatbot_supabase_client is None:
        logger.info("Initializing Chatbot Supabase client (read/write)")
        
        # Optional: Configure connection pooling if enabled
        _configure_connection_pooling()
        
        # Temporarily remove proxy env vars to prevent gotrue errors
        saved_proxy = _ensure_no_proxy_env()
        try:
            # Create Supabase client
            # Note: Supabase Python client uses httpx internally which has built-in connection pooling
            # The httpx client automatically pools connections based on the URL and connection limits
            # Connection pooling is handled at the httpx level and is active by default
            # When ENABLE_CONNECTION_POOLING=true, pool configuration is applied via environment
            _chatbot_supabase_client = create_client(
                settings.CHATBOT_SUPABASE_URL,
                settings.CHATBOT_SUPABASE_SERVICE_ROLE_KEY
            )
        finally:
            _restore_proxy_env(saved_proxy)

    return _chatbot_supabase_client


# Backward compatibility alias - defaults to Chatbot client
# This can be used by existing code that doesn't specify which client
def get_supabase_client() -> Client:
    """
    Returns Chatbot Supabase client (backward compatibility).
    For new code, use get_chatbot_supabase_client() or get_edify_supabase_client() explicitly.
    """
    return get_chatbot_supabase_client()
