from typing import Dict, Any, Optional
from app.langgraph.state import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.config import settings
import logging
import re
import os

logger = logging.getLogger(__name__)

# Greeting keywords for detection
GREETING_KEYWORDS = [
    "hi", "hello", "hey", "hii", "hiii", "hiiii",
    "good morning", "good afternoon", "good evening",
    "morning", "afternoon", "evening",
    "greetings", "greeting",
    "hi there", "hello there", "hey there"
]

def is_greeting(message: str) -> bool:
    """
    Detects if a message is a greeting.
    Case-insensitive, trims whitespace.
    """
    if not message:
        return False
    
    # Normalize: lowercase, trim whitespace
    normalized = message.strip().lower()
    
    # Check exact match or starts with greeting keyword
    for keyword in GREETING_KEYWORDS:
        if normalized == keyword or normalized.startswith(keyword + " "):
            return True
    
    return False

def get_greeting_response() -> str:
    """
    Returns a friendly, professional greeting response.
    """
    return "Hii 👋\nWhat's up? How can I help you today?"

def normalize_input(text: str) -> str:
    """
    Normalizes user input for robust matching.
    - Convert to lowercase
    - Trim spaces
    - Remove punctuation
    - Normalize plural/singular
    """
    if not text:
        return ""
    
    # Lowercase and trim
    normalized = text.strip().lower()
    
    # Remove punctuation (keep spaces and alphanumeric)
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Normalize plural/singular (simple approach)
    # Remove trailing 's' for common words (leads -> lead, trainers -> trainer)
    # But keep context-aware (e.g., "courses" -> "course")
    words = normalized.split()
    normalized_words = []
    for word in words:
        # Remove trailing 's' if word is longer than 3 chars (to avoid removing 'is', 'as', etc.)
        if len(word) > 3 and word.endswith('s'):
            normalized_words.append(word[:-1])
        else:
            normalized_words.append(word)
    
    return ' '.join(normalized_words)

def detect_intent_keywords(query: str) -> Optional[str]:
    """
    CRM-only intent detection.
    All queries default to CRM since SalesBot only handles CRM operations.
    Returns "crm" for all valid queries, None only for greetings.
    """
    normalized = normalize_input(query)
    
    # CRM keywords (comprehensive list)
    crm_keywords = [
        # Leads
        'lead', 'leads', 'prospect', 'prospects', 'enquiry', 'enquiry', 'inquiry', 'inquiries',
        'customer lead', 'crm lead', 'crm leads',
        # Trainers
        'trainer', 'trainers', 'instructor', 'instructors',
        # Learners
        'learner', 'learners', 'student', 'students',
        # Campaigns
        'campaign', 'campaigns', 'marketing campaign',
        # Tasks
        'task', 'tasks', 'todo', 'todos',
        # Activities
        'activity', 'activities', 'log', 'logs',
        # Notes
        'note', 'notes', 'comment', 'comments',
        # Courses (in CRM)
        'course', 'courses', 'program', 'programs',
        # Generic CRM
        'crm', 'crm data', 'crm information'
    ]
    
    # Check for CRM keywords
    for keyword in crm_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"CRM intent detected via keyword: {keyword}")
            return "crm"
    
    # Default to CRM for all other queries (SalesBot is CRM-only)
    return "crm"

def decide_source_node(state: AgentState) -> Dict[str, Any]:
    """
    Decides which data source to query based on user_message.
    Uses LENIENT intent detection: keyword-based first, then LLM fallback.
    """
    try:
        user_message = state["user_message"]
        
        # Check for greeting first (no LLM call needed)
        if is_greeting(user_message):
            logger.info("Greeting detected, skipping data retrieval")
            return {
                "source_type": "none",
                "response": get_greeting_response()
            }
        
        # STEP 1: Try robust keyword-based intent detection (LENIENT)
        keyword_intent = detect_intent_keywords(user_message)
        if keyword_intent:
            logger.info(f"Intent detected via keywords: {keyword_intent}")
            return {"source_type": keyword_intent}
        
        # STEP 2: Default to CRM (SalesBot is CRM-only)
        # No LLM fallback needed - all queries route to CRM
        logger.info("Defaulting to CRM (SalesBot is CRM-only)")
        return {"source_type": "crm"}
        
    except Exception as e:
        logger.error(f"Error in decide_source: {e}", exc_info=True)
        return {"source_type": "general"} # Default to general to avoid crash
