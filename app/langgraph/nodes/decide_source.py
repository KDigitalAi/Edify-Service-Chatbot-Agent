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

def detect_followup_intent(query: str) -> bool:
    """
    Detects if query is about follow-up reminders.
    Returns True if follow-up intent detected.
    
    IMPORTANT: Excludes queries containing "send" - those are actions, not queries.
    """
    normalized = normalize_input(query)
    
    # EXCLUDE queries that contain "send" - those are email sending actions, not follow-up queries
    if re.search(r'\bsend\b', normalized):
        return False  # Don't treat as follow-up query if user wants to send email
    
    # Follow-up keywords
    followup_keywords = [
        'follow up', 'follow-up', 'followup',
        'pending lead', 'pending leads',
        'lead to call', 'leads to call',
        'followup today', 'follow up today',
        'requiring follow', 'need follow',
        'due follow', 'overdue follow',
        'reminder', 'reminders'
    ]
    
    # Check for follow-up keywords
    for keyword in followup_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"Follow-up intent detected via keyword: {keyword}")
            return True
    
    return False

def detect_send_email_intent(query: str) -> bool:
    """
    Detects if query is about sending an email.
    Returns True if send email intent detected.
    """
    normalized = normalize_input(query)
    
    # Send email keywords (must be explicit)
    send_keywords = [
        'send email', 'send mail', 'send this email', 'send this mail',
        'email now', 'mail now', 'send it', 'dispatch email', 'dispatch mail',
        'send the email', 'send the mail'
    ]
    
    # Check for send keywords
    has_send_keyword = any(
        re.search(rf'\b{re.escape(keyword)}\b', normalized)
        for keyword in send_keywords
    )
    
    # Also check for "send" + "email" pattern even if separated by words (e.g., "send follow-up email")
    # Pattern: "send" followed by optional words, then "email" or "mail"
    has_send_email_pattern = (
        re.search(r'\bsend\b', normalized) and 
        (re.search(r'\bemail\b', normalized) or re.search(r'\bmail\b', normalized))
    )
    
    if has_send_keyword or has_send_email_pattern:
        logger.info(f"Send email intent detected: '{query[:50]}...'")
        return True
    
    return False

def detect_email_draft_intent(query: str) -> bool:
    """
    Detects if query is about email draft generation.
    Returns True if email draft intent detected.
    """
    normalized = normalize_input(query)
    
    # Email draft keywords (comprehensive list)
    email_keywords = [
        'draft email', 'draft mail', 'write email', 'write mail',
        'compose email', 'compose mail', 'create email', 'create mail',
        'email draft', 'mail draft', 'follow-up email', 'followup email',
        'follow-up mail', 'followup mail'
    ]
    
    # Check for email draft keywords (but NOT send keywords)
    has_email_keyword = any(
        re.search(rf'\b{re.escape(keyword)}\b', normalized)
        for keyword in email_keywords
    )
    
    # Must NOT have send keywords (to distinguish from send intent)
    has_send_keyword = any(
        re.search(rf'\b{re.escape(keyword)}\b', normalized)
        for keyword in ['send', 'dispatch', 'now']
    )
    
    if has_email_keyword and not has_send_keyword:
        logger.info(f"Email draft intent detected: '{query[:50]}...'")
        return True
    
    return False

def detect_lead_summary_intent(query: str) -> bool:
    """
    Detects if query is about lead activity summary.
    Returns True if lead summary intent detected.
    Handles various query formats dynamically.
    """
    normalized = normalize_input(query)
    
    # Lead summary keywords (comprehensive list)
    summary_keywords = [
        'summary', 'full summary', 'activity summary',
        'lead summary', 'full history', 'activity history',
        'lead activity', 'lead history', 'complete summary',
        'history of lead', 'show activity', 'activity of lead'
    ]
    
    # Check for summary keywords AND lead-related terms
    has_summary_keyword = any(
        re.search(rf'\b{re.escape(keyword)}\b', normalized)
        for keyword in summary_keywords
    )
    
    # Also check for lead-related terms
    has_lead_term = any(
        re.search(rf'\b{re.escape(term)}\b', normalized)
        for term in ['lead', 'leads', 'prospect', 'customer']
    )
    
    # Must have both summary keyword AND lead term
    if has_summary_keyword and has_lead_term:
        logger.info(f"Lead summary intent detected: '{query[:50]}...'")
        return True
    
    # Also detect patterns like "history of lead X" or "summary for lead Y"
    # This handles "Give me full summary of lead guna"
    if re.search(r'\b(history|summary|activity|full)\s+(of|for)\s+lead', normalized):
        logger.info(f"Lead summary intent detected via pattern: '{query[:50]}...'")
        return True
    
    # Detect "full summary of lead" pattern (handles "Give me full summary of lead guna")
    if re.search(r'full\s+summary\s+of\s+lead', normalized):
        logger.info(f"Lead summary intent detected via 'full summary of lead' pattern")
        return True
    
    return False

def detect_intent_keywords(query: str) -> Optional[str]:
    """
    CRM-only intent detection.
    All queries default to CRM since SalesBot only handles CRM operations.
    Returns "crm" for all valid queries, None only for greetings.
    
    Priority order:
    Greeting → Send Email → Follow-up → Draft Email → Lead Summary → CRM
    """
    normalized = normalize_input(query)
    
    # Check for send email intent FIRST (actions take priority over queries)
    if detect_send_email_intent(query):
        return "send_email"
    
    # Check for follow-up intent (only if not sending email)
    if detect_followup_intent(query):
        return "followup"
    
    # Check for email draft intent (higher priority than lead summary)
    if detect_email_draft_intent(query):
        return "email_draft"
    
    # Check for lead summary intent (higher priority than general CRM)
    if detect_lead_summary_intent(query):
        return "lead_summary"
    
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
            logger.info(f"[DECIDE_SOURCE] Intent detected via keywords: {keyword_intent} for query: '{user_message[:80]}...'")
            return {"source_type": keyword_intent}
        
        # STEP 2: Default to CRM (SalesBot is CRM-only)
        # No LLM fallback needed - all queries route to CRM
        logger.info("Defaulting to CRM (SalesBot is CRM-only)")
        return {"source_type": "crm"}
        
    except Exception as e:
        logger.error(f"Error in decide_source: {e}", exc_info=True)
        return {"source_type": "general"} # Default to general to avoid crash
