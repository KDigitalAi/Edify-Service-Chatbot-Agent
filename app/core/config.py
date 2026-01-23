from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

def _parse_bool(value: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    if not value:
        return default
    return value.lower() in ("true", "1", "yes", "on")

def _parse_int(value: str, default: int) -> int:
    """Parse integer from environment variable."""
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default

class Settings(BaseModel):
    """
    Application settings loaded from environment variables.
    Supports dual Supabase configuration:
    - Edify Supabase: Read-only data source (CRM/LMS/RMS)
    - Chatbot Supabase: Read/write database (sessions/memory/RAG/audit)
    
    Optimization features are optional and can be enabled via environment variables.
    All optimizations are non-breaking and disabled by default.
    """
    # OpenAI Configuration
    OPENAI_API_KEY: str
    
    # Edify Supabase (READ-ONLY)
    EDIFY_SUPABASE_URL: str
    EDIFY_SUPABASE_SERVICE_ROLE_KEY: str
    
    # Chatbot Supabase (READ/WRITE)
    CHATBOT_SUPABASE_URL: str
    CHATBOT_SUPABASE_SERVICE_ROLE_KEY: str
    
    # Environment Configuration
    ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # Optional Optimization Features (disabled by default)
    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = False
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100
    
    # Caching (Redis)
    ENABLE_CACHING: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default
    
    # Connection Pooling
    ENABLE_CONNECTION_POOLING: bool = False
    MAX_CONNECTIONS: int = 100
    
    # Request Timeouts
    ENABLE_REQUEST_TIMEOUT: bool = False
    REQUEST_TIMEOUT_SECONDS: int = 30
    
    # CORS Configuration
    CORS_ALLOW_ORIGINS: str = "*"  # Comma-separated list or "*" for all
    
    # Response Compression
    ENABLE_COMPRESSION: bool = False
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    
    # Query Optimization (disabled by default)
    ENABLE_QUERY_OPTIMIZATION: bool = False  # Select specific fields instead of *
    ENABLE_QUERY_RETRY: bool = False  # Retry failed queries with exponential backoff
    QUERY_RETRY_MAX_ATTEMPTS: int = 3
    QUERY_RETRY_INITIAL_DELAY_MS: int = 100
    
    # LLM Response Caching (disabled by default)
    ENABLE_LLM_CACHING: bool = False
    LLM_CACHE_TTL_SECONDS: int = 3600  # 1 hour default
    
    # Parallel Operations (disabled by default)
    ENABLE_PARALLEL_FETCHING: bool = False  # Fetch from multiple sources in parallel
    
    # Async DB Operations (disabled by default)
    ENABLE_ASYNC_DB: bool = False  # Execute synchronous DB calls in thread pool
    
    # Async Writes (disabled by default)
    ENABLE_ASYNC_WRITES: bool = False  # Move context saving off main request path using background tasks

settings = Settings(
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
    EDIFY_SUPABASE_URL=os.getenv("EDIFY_SUPABASE_URL", ""),
    EDIFY_SUPABASE_SERVICE_ROLE_KEY=os.getenv("EDIFY_SUPABASE_SERVICE_ROLE_KEY", ""),
    CHATBOT_SUPABASE_URL=os.getenv("CHATBOT_SUPABASE_URL", ""),
    CHATBOT_SUPABASE_SERVICE_ROLE_KEY=os.getenv("CHATBOT_SUPABASE_SERVICE_ROLE_KEY", ""),
    ENV=os.getenv("ENV", "local"),
    LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
    # Optional optimizations (disabled by default)
    ENABLE_RATE_LIMITING=_parse_bool(os.getenv("ENABLE_RATE_LIMITING", "false")),
    RATE_LIMIT_PER_MINUTE=_parse_int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"), 10),
    RATE_LIMIT_PER_HOUR=_parse_int(os.getenv("RATE_LIMIT_PER_HOUR", "100"), 100),
    ENABLE_CACHING=_parse_bool(os.getenv("ENABLE_CACHING", "false")),
    REDIS_HOST=os.getenv("REDIS_HOST", "localhost"),
    REDIS_PORT=_parse_int(os.getenv("REDIS_PORT", "6379"), 6379),
    REDIS_DB=_parse_int(os.getenv("REDIS_DB", "0"), 0),
    REDIS_PASSWORD=os.getenv("REDIS_PASSWORD", ""),
    CACHE_TTL_SECONDS=_parse_int(os.getenv("CACHE_TTL_SECONDS", "300"), 300),
    ENABLE_CONNECTION_POOLING=_parse_bool(os.getenv("ENABLE_CONNECTION_POOLING", "false")),
    MAX_CONNECTIONS=_parse_int(os.getenv("MAX_CONNECTIONS", "100"), 100),
    ENABLE_REQUEST_TIMEOUT=_parse_bool(os.getenv("ENABLE_REQUEST_TIMEOUT", "false")),
    REQUEST_TIMEOUT_SECONDS=_parse_int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"), 30),
    CORS_ALLOW_ORIGINS=os.getenv("CORS_ALLOW_ORIGINS", "*"),
    ENABLE_COMPRESSION=_parse_bool(os.getenv("ENABLE_COMPRESSION", "false")),
    DEFAULT_PAGE_SIZE=_parse_int(os.getenv("DEFAULT_PAGE_SIZE", "50"), 50),
    MAX_PAGE_SIZE=_parse_int(os.getenv("MAX_PAGE_SIZE", "200"), 200),
    # Query optimization flags (disabled by default)
    ENABLE_QUERY_OPTIMIZATION=_parse_bool(os.getenv("ENABLE_QUERY_OPTIMIZATION", "false")),
    ENABLE_QUERY_RETRY=_parse_bool(os.getenv("ENABLE_QUERY_RETRY", "false")),
    QUERY_RETRY_MAX_ATTEMPTS=_parse_int(os.getenv("QUERY_RETRY_MAX_ATTEMPTS", "3"), 3),
    QUERY_RETRY_INITIAL_DELAY_MS=_parse_int(os.getenv("QUERY_RETRY_INITIAL_DELAY_MS", "100"), 100),
    # LLM caching (disabled by default)
    ENABLE_LLM_CACHING=_parse_bool(os.getenv("ENABLE_LLM_CACHING", "false")),
    LLM_CACHE_TTL_SECONDS=_parse_int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"), 3600),
    # Parallel operations (disabled by default)
    ENABLE_PARALLEL_FETCHING=_parse_bool(os.getenv("ENABLE_PARALLEL_FETCHING", "false")),
    # Async DB operations (disabled by default)
    ENABLE_ASYNC_DB=_parse_bool(os.getenv("ENABLE_ASYNC_DB", "false")),
    # Async writes (disabled by default)
    ENABLE_ASYNC_WRITES=_parse_bool(os.getenv("ENABLE_ASYNC_WRITES", "false")),
)
