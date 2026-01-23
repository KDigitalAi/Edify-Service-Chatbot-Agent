from typing import Dict, Any, Optional
from app.langgraph.state import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.config import settings
import logging
import re

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
    Robust keyword-based intent detection (LENIENT approach).
    Detects CRM/LMS/RMS/RAG intent using keyword matching.
    Returns source type or None if unclear.
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
    
    # LMS keywords
    lms_keywords = [
        'batch', 'batches', 'training batch', 'lms batch', 'lms batches',
        'batch schedule', 'batch schedules', 'lms'
    ]
    
    # RMS keywords
    rms_keywords = [
        'candidate', 'candidates', 'recruitment', 'job', 'jobs',
        'position', 'positions', 'rms', 'rms candidate', 'rms candidates',
        'job opening', 'job openings', 'opening', 'openings', 'vacancy', 'vacancies',
        'interview', 'interviews', 'screening', 'screenings',
        'company', 'companies', 'organization', 'organizations', 'employer', 'employers',
        'hiring', 'hiring manager', 'recruiter', 'recruiters'
    ]
    
    # RAG keywords
    rag_keywords = [
        'policy', 'policies', 'document', 'documents', 'knowledge base',
        'knowledge', 'guide', 'guides', 'manual', 'manuals', 'rag'
    ]
    
    # Check for CRM keywords (most comprehensive)
    for keyword in crm_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"CRM intent detected via keyword: {keyword}")
            return "crm"
    
    # Check for LMS keywords
    for keyword in lms_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"LMS intent detected via keyword: {keyword}")
            return "lms"
    
    # Check for RMS keywords
    for keyword in rms_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"RMS intent detected via keyword: {keyword}")
            return "rms"
    
    # Check for RAG keywords
    for keyword in rag_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', normalized):
            logger.info(f"RAG intent detected via keyword: {keyword}")
            return "rag"
    
    return None

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
        
        # STEP 2: Fallback to LLM for ambiguous cases
        logger.info("No clear keyword match, using LLM for classification")
        llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o")
        
        system_prompt = """You are a router. Classify the user's request into the correct data source.

        IMPORTANT: CRM contains ALL of these entities:
        - Leads, Prospects, Customers
        - Trainers, Instructors (NOT in LMS - they are in CRM)
        - Learners, Students (NOT in LMS - they are in CRM)
        - Campaigns, Marketing campaigns
        - Tasks, Todos
        - Activities, Activity logs
        - Notes, Comments
        - Courses (Course table is in CRM, not LMS)
        
        Categories:
        - "crm": All CRM data including Leads, Trainers, Learners, Campaigns, Tasks, Activities, Notes, Courses
        - "lms": Training batches and batch schedules only (NOT trainers or learners - those are in CRM)
        - "rms": Candidate/Job/Recruitment data including Job Openings, Candidates, Companies, Interviews, and RMS Tasks
        - "rag": Policy/Knowledge base/Documents
        - "general": Off-topic or unclear requests
        
        CRITICAL RULES:
        1. Trainers/Instructors → ALWAYS "crm" (NOT "lms")
        2. Learners/Students → ALWAYS "crm" (NOT "lms")
        3. Courses → "crm" (Course table is in CRM)
        4. Only training batches/schedules → "lms"
        5. Job openings, positions, vacancies, candidates, interviews, companies → "rms"
        6. Tasks in recruitment context → "rms", otherwise "crm"
        
        Return ONLY the category name.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        
        chain = prompt | llm
        result = chain.invoke({"input": user_message})
        source = result.content.strip().lower()
        
        valid_sources = ["crm", "lms", "rms", "rag", "general"]
        if source not in valid_sources:
            source = "general"
            
        logger.info(f"Decided source: {source}")
        
        return {"source_type": source}
        
    except Exception as e:
        logger.error(f"Error in decide_source: {e}", exc_info=True)
        return {"source_type": "general"} # Default to general to avoid crash
