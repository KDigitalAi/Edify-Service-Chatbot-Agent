from typing import Any
import json
import re
import hashlib
from app.llm.openai_client import OpenAIClient
from app.utils.cache import get_cached, set_cached, cache_key_llm_response
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ResponseFormatter:
    def __init__(self):
        self.client = OpenAIClient()
    
    def fix_numbered_list(self, text: str) -> str:
        """
        Post-processes the response to fix numbered list formatting.
        Ensures sequential numbering (1, 2, 3, etc.) even if LLM generates incorrect numbering.
        Specifically fixes cases where all items are numbered as "1."
        """
        if not text:
            return text
        
        lines = text.split('\n')
        fixed_lines = []
        list_counter = 1
        in_numbered_list = False
        
        for i, line in enumerate(lines):
            # Check if this line starts with a numbered list pattern: "1.", "2.", etc.
            # Pattern: optional whitespace, number, period, space, then content
            number_match = re.match(r'^(\s*)(\d+)\.\s+(.+)', line)
            
            if number_match:
                # This is a numbered list item
                indent = number_match.group(1)
                original_number = int(number_match.group(2))
                content = number_match.group(3)
                
                if in_numbered_list:
                    # We're continuing a list
                    # If we see "1." again, it's a duplicate - use our counter
                    if original_number == 1:
                        # Duplicate "1." detected - use sequential number
                        fixed_line = f"{indent}{list_counter}. {content}"
                        list_counter += 1
                    elif original_number == list_counter:
                        # Correct sequential number
                        fixed_line = f"{indent}{list_counter}. {content}"
                        list_counter += 1
                    else:
                        # Number jumped - use our counter
                        fixed_line = f"{indent}{list_counter}. {content}"
                        list_counter += 1
                else:
                    # Starting a new numbered list
                    list_counter = 1
                    fixed_line = f"{indent}{list_counter}. {content}"
                    list_counter += 1
                    in_numbered_list = True
                
                fixed_lines.append(fixed_line)
            else:
                # Not a numbered list item
                fixed_lines.append(line)
                
                # Determine if we should reset list context
                line_stripped = line.strip()
                
                if not line_stripped:
                    # Blank line - check if list continues after
                    # Look ahead a few lines
                    continues = False
                    for j in range(i + 1, min(i + 4, len(lines))):
                        if re.match(r'^\s*\d+\.\s+', lines[j]):
                            continues = True
                            break
                    if not continues:
                        in_numbered_list = False
                        list_counter = 1
                elif not line.startswith((' ', '\t', '-')) and not re.match(r'^\s*[-*]\s+', line):
                    # Non-indented, non-list line - likely new section
                    # Check if next lines continue the list
                    continues = False
                    for j in range(i + 1, min(i + 3, len(lines))):
                        if re.match(r'^\s*\d+\.\s+', lines[j]):
                            continues = True
                            break
                    if not continues:
                        in_numbered_list = False
                        list_counter = 1
        
        return '\n'.join(fixed_lines)

    def format_response(self, query: str, context: Any, source: str) -> str:
        """
        Formats the retrieved context into a polite response.
        """
        try:
            if not context and source != "general":
                return "I searched the records but found no matching data for your request."

            # Construct System Prompt based on source
            if source == "general":
                 system_prompt = """You are a helpful and professional Edify Admin Assistant. 
                 Your role is to assist administrators. 
                 Answer general greetings or navigational questions politely.
                 WARN: Do not invent any business data (names, deals, courses) if not provided.
                 """
                 user_input = query
            else:
                 # Serialize context safely
                 context_str = json.dumps(context, indent=2, default=str)
                 
                 system_prompt = f"""You are a helpful Edify Admin Assistant.
                 Your task is to answer the user's query using ONLY the provided context from the {source.upper()} system.
                 
                 RULES:
                 1. Use ONLY the provided context.
                 2. Do not invent information.
                 3. If the context does not answer the question, say "The provided records do not contain the answer."
                 4. Create a clean, readable response (use numbered lists, bullet points, or tables if data is structured).
                 
                 CRITICAL FORMATTING RULES:
                 - When creating numbered lists, ALWAYS use sequential numbering: 1, 2, 3, 4, etc.
                 - NEVER repeat the same number (e.g., don't use "1." for multiple items).
                 - Each item in a numbered list must have a unique, incrementing number.
                 - Example of CORRECT format:
                   1. First item
                   2. Second item
                   3. Third item
                 - Example of WRONG format (DO NOT DO THIS):
                   1. First item
                   1. Second item
                   1. Third item
                 
                 CONTEXT:
                 {context_str}
                 """
                 user_input = query
            
            # Optional: Try LLM response cache first (non-breaking if cache unavailable)
            if settings.ENABLE_LLM_CACHING:
                # Generate cache key from query and context hash
                context_hash = hashlib.md5(json.dumps(context, default=str, sort_keys=True).encode()).hexdigest()
                cache_key = cache_key_llm_response(query, context_hash)
                cached_response = get_cached(cache_key)
                if cached_response is not None:
                    logger.debug(f"Cache hit for LLM response")
                    # Still post-process cached response
                    return self.fix_numbered_list(cached_response)

            response = self.client.generate_response(system_prompt, user_input)
            
            # Optional: Cache LLM response (non-breaking if cache fails)
            if settings.ENABLE_LLM_CACHING:
                set_cached(cache_key, response, ttl=settings.LLM_CACHE_TTL_SECONDS)
            
            # Post-process to fix numbered list formatting
            response = self.fix_numbered_list(response)
            
            return response

        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return "I encountered an error while formatting the data."
