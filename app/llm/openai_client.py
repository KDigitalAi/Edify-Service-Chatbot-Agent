from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.utils.cache import get_cached, set_cached
import logging
import hashlib

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o",
            temperature=0  # Deterministic for formatting
        )
    
    def _generate_cache_key(self, system_prompt: str, user_input: str) -> str:
        """
        Generate cache key from prompt and context.
        Uses hash of system_prompt + user_input for consistent caching.
        """
        combined = f"{system_prompt}:{user_input}"
        prompt_hash = hashlib.md5(combined.encode()).hexdigest()
        return f"llm_response:openai:{prompt_hash}"

    def generate_response(self, system_prompt: str, user_input: str) -> str:
        """
        Generates a response from the LLM.
        Optional caching: If ENABLE_LLM_CACHING is True, caches responses based on prompt hash.
        TTL: 10 minutes (600 seconds) for response caching.
        
        Args:
            system_prompt: System prompt for the LLM
            user_input: User input/query
            
        Returns:
            LLM response string (never modified)
        """
        # Optional: Try cache first (non-breaking if cache unavailable)
        if settings.ENABLE_LLM_CACHING:
            cache_key = self._generate_cache_key(system_prompt, user_input)
            cached_response = get_cached(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for LLM response (prompt hash: {cache_key[-8:]})")
                # Return cached response without modification
                return cached_response
        
        # Cache miss: Call OpenAI as before
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            response = self.llm.invoke(messages)
            response_content = response.content
            
            # Optional: Cache the response (non-breaking if cache fails)
            # TTL: 10 minutes (600 seconds) as specified
            if settings.ENABLE_LLM_CACHING:
                cache_key = self._generate_cache_key(system_prompt, user_input)
                set_cached(cache_key, response_content, ttl=600)  # 10 minutes
                logger.debug(f"Cached LLM response (prompt hash: {cache_key[-8:]})")
            
            # Return response without modification
            return response_content
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise e
