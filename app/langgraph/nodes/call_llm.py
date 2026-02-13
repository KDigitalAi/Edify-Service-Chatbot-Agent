from typing import Dict, Any, List
from app.langgraph.state import AgentState
from app.llm.formatter import ResponseFormatter
from app.services.tool_registry import ToolRegistry
from app.db.audit_repo import AuditRepo
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import logging
import os
import json

logger = logging.getLogger(__name__)

def _detect_action_intent(query: str, has_pending_action: bool = False) -> bool:
    """
    Detect if user wants to perform an action (create, update, delete).
    If there's a pending action, confirmation messages are NOT treated as new actions.
    Returns True if action intent detected.
    """
    # If there's a pending action, check if this is a confirmation
    if has_pending_action:
        confirmation_keywords = ["yes", "confirm", "proceed", "delete", "ok", "okay", "yep", "sure", "y", "go ahead", "do it", "cancel", "no", "abort"]
        query_lower = query.lower().strip()
        # If it's just a confirmation/cancellation, don't treat as new action
        if any(keyword in query_lower for keyword in confirmation_keywords) and len(query_lower.split()) <= 3:
            return False
    
    query_lower = query.lower()
    action_keywords = [
        "create", "add", "new", "insert", "make",
        "update", "change", "modify", "edit", "set",
        "delete", "remove", "cancel", "drop"
    ]
    return any(keyword in query_lower for keyword in action_keywords)

def call_llm_node(state: AgentState) -> Dict[str, Any]:
    """
    Calls LLM to format response or execute agentic actions.
    Uses function calling for actions, regular formatting for queries.
    """
    try:
        context = state.get("retrieved_context")
        source = state.get("source_type", "general")
        query = state["user_message"]
        session_id = state.get("session_id")
        admin_id = state.get("admin_id", "anonymous")
        action_results = state.get("action_results")
        
        # ENTITY MEMORY: Extract entity memory from state
        entity_memory = {}
        for key, value in state.items():
            if key.startswith("last_") and value:
                entity_memory[key] = value
        
        # If response already set, skip
        if state.get("response"):
            return {}

        # If we have action results, format them into a response and clear tool_calls
        if action_results and len(action_results) > 0:
            formatted = _format_action_results(action_results, query)
            # Clear tool_calls to prevent recursion loop
            formatted["tool_calls"] = None
            return formatted

        # Check if there's a pending action requiring confirmation
        has_pending_action = state.get("requires_confirmation", False) and state.get("pending_action") is not None
        
        # Check if user wants to perform an action
        # If there's a pending action, confirmation messages are NOT treated as new actions
        is_action = _detect_action_intent(query, has_pending_action)
        
        if is_action:
            # Use function calling for agentic actions
            # Inject entity memory into query context for LLM
            return _call_llm_with_functions(query, context, admin_id, session_id, entity_memory)
        else:
            # Regular query - use formatter
            # CONTEXT REQUIREMENT: LLM must have Edify context (except greetings handled by decide_source)
            is_context_empty = (
                context is None or 
                (isinstance(context, list) and len(context) == 0) or
                (isinstance(context, dict) and len(context) == 0)
            )
            
            # If no context and not a greeting, reject
            if is_context_empty:
                from app.langgraph.nodes.decide_source import is_greeting
                if not is_greeting(query):
                    logger.warning(f"Blocked LLM call without context for query: {query[:100]}")
                    return {
                        "response": "I can only answer questions related to Edify CRM data."
                    }

            formatter = ResponseFormatter()
            response = formatter.format_response(query, context, source)
            
            return {"response": response}

    except Exception as e:
        logger.error(f"Error calling LLM: {e}", exc_info=True)
        # Persist error to audit log
        try:
            audit = AuditRepo()
            audit.log_action(
                admin_id=admin_id,
                action="llm_error",
                details={
                    "error": str(e),
                    "source_type": state.get("source_type"),
                    "query": query[:100]
                },
                session_id=session_id
            )
        except:
            pass
        return {"response": "I encountered an error generating the response."}

def _call_llm_with_functions(query: str, context: Any, admin_id: str, session_id: str, entity_memory: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Call LLM with function calling enabled for agentic actions.
    """
    try:
        registry = ToolRegistry()
        tool_schemas = registry.get_tool_schemas()
        
        # Build entity memory context for LLM
        # Generic approach - works for ALL CRM entities
        memory_context = ""
        if entity_memory:
            # Use generic last_entity fields if available
            last_entity_type = entity_memory.get("last_entity_type")
            last_entity_id = entity_memory.get("last_entity_id")
            last_entity_name = entity_memory.get("last_entity_name")
            
            if last_entity_type and last_entity_id:
                memory_items = [f"Last {last_entity_type} ID: {last_entity_id}"]
                if last_entity_name:
                    memory_items.append(f"Last {last_entity_type} name: {last_entity_name}")
                
                memory_context = (
                    "\n\nConversation Context (use these values if user doesn't specify):\n" +
                    "\n".join(memory_items) +
                    "\n\nWhen user says 'update it', 'change the phone', 'modify this', 'delete that', etc., "
                    f"use the last {last_entity_type} ID ({last_entity_id}) from context. "
                    "Do NOT ask for the ID again if it's already in context."
                )
        
        # Build system prompt for agentic actions
        system_prompt = f"""You are SalesBot, an AI assistant for CRM operations.
You can perform actions like creating leads, updating records, creating tasks, etc.

When the user wants to perform an action:
1. Use the appropriate function/tool
2. Extract all required information from the user's message
3. If information is missing, check conversation context below
4. If still missing, ask the user for it
5. Only call functions when you have enough information

{memory_context}

For queries (not actions), provide helpful responses based on the context.

Available CRM operations:
- Create, update, delete leads
- Create, update campaigns
- Create, update tasks
- Create, update trainers and learners
- Create, update courses
- Create activities and notes

Always be helpful and confirm actions clearly."""
        
        # Temporarily remove proxy env vars
        saved_proxy_vars = {}
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        for var in proxy_vars:
            if var in os.environ:
                saved_proxy_vars[var] = os.environ.pop(var)
        
        try:
            # Create LLM with function calling
            llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4o",
                temperature=0
            )
            
            # Bind tools to LLM using OpenAI function calling format
            # LangChain's bind_tools accepts list of dict schemas
            llm_with_tools = llm.bind_tools(tool_schemas)
            
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            
            # Invoke LLM
            response = llm_with_tools.invoke(messages)
            
            # Check for tool calls
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    # Extract tool call information
                    tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
                    tool_args_str = tool_call.get("args") or tool_call.get("function", {}).get("arguments", "{}")
                    
                    # Parse arguments if it's a string
                    if isinstance(tool_args_str, str):
                        try:
                            tool_args = json.loads(tool_args_str)
                        except:
                            tool_args = {}
                    else:
                        tool_args = tool_args_str
                    
                    tool_calls.append({
                        "name": tool_name,
                        "arguments": tool_args
                    })
                    logger.info(f"LLM requested tool call: {tool_name} with args: {list(tool_args.keys())}")
            
            # If tool calls were made, return them for execution
            if tool_calls:
                return {
                    "tool_calls": tool_calls
                }
            else:
                # No tool calls - LLM provided a text response
                return {
                    "response": response.content if hasattr(response, 'content') else str(response)
                }
                
        finally:
            # Restore proxy env vars
            os.environ.update(saved_proxy_vars)
            
    except Exception as e:
        logger.error(f"Error in function calling: {e}", exc_info=True)
        return {
            "response": "I encountered an error processing your request. Please try again."
        }

def _format_action_results(action_results: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
    """
    Format action results into a user-friendly response.
    """
    responses = []
    
    for result in action_results:
        tool_name = result.get("tool_name", "action")
        status = result.get("status")
        
        if status == "success":
            result_data = result.get("result", {})
            action_name = tool_name.replace("_", " ").title()
            
            # CRITICAL: Do NOT fabricate IDs - database is single source of truth
            # Extract key information from result - only use real IDs from database
            if isinstance(result_data, dict):
                # For delete operations, result may be {"deleted": True}
                if result_data.get("deleted") is True:
                    responses.append(f"Successfully {action_name}")
                # For create/update operations, must have real ID
                elif "id" in result_data and result_data.get("id"):
                    record_id = result_data.get("id")
                    name = result_data.get("name") or result_data.get("trainer_name") or result_data.get("title") or result_data.get("subject")
                    
                    if name:
                        responses.append(f"Successfully {action_name}: {name} (ID: {record_id})")
                    else:
                        responses.append(f"Successfully completed {action_name} (ID: {record_id})")
                else:
                    # Missing ID - this should not happen if validation worked correctly
                    error_msg = f"{action_name} failed - no record returned from database (missing ID)"
                    logger.error(f"Invalid success result for {tool_name}: {result_data}")
                    responses.append(error_msg)
            else:
                # Invalid result structure - should not happen
                error_msg = f"{action_name} failed - invalid result structure"
                logger.error(f"Invalid result type for {tool_name}: {type(result_data)}")
                responses.append(error_msg)
                
        elif status == "cancelled":
            responses.append("Action was cancelled.")
            
        elif status == "error":
            error = result.get("error", "Unknown error")
            responses.append(f"Error: {error}")
    
    if responses:
        return {
            "response": "\n".join(responses)
        }
    else:
        return {
            "response": "Action completed."
        }
