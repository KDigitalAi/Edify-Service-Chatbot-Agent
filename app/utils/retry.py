"""
Optional retry utilities with exponential backoff.
Only active if ENABLE_QUERY_RETRY is True in settings.
Non-breaking: Falls back to single attempt if retry disabled.
"""
from typing import Callable, TypeVar, Optional, Any
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: Optional[int] = None,
    initial_delay_ms: Optional[int] = None,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Retry a function with exponential backoff.
    Only active if ENABLE_QUERY_RETRY is True.
    Non-breaking: Falls back to single attempt if retry disabled.
    
    Args:
        func: Function to retry (no arguments)
        max_attempts: Maximum retry attempts (defaults to settings)
        initial_delay_ms: Initial delay in milliseconds (defaults to settings)
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all retries fail
    """
    if not settings.ENABLE_QUERY_RETRY:
        # Retry disabled - execute once
        return func()
    
    max_attempts = max_attempts or settings.QUERY_RETRY_MAX_ATTEMPTS
    initial_delay_ms = initial_delay_ms or settings.QUERY_RETRY_INITIAL_DELAY_MS
    
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_attempts:
                # Calculate exponential backoff delay
                delay_ms = initial_delay_ms * (2 ** (attempt - 1))
                delay_seconds = delay_ms / 1000.0
                
                logger.debug(f"Retry attempt {attempt}/{max_attempts} after {delay_seconds:.2f}s: {str(e)[:100]}")
                time.sleep(delay_seconds)
            else:
                logger.warning(f"All {max_attempts} retry attempts failed")
    
    # All retries exhausted
    raise last_exception

