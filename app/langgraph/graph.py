from langgraph.graph import StateGraph, END
from app.langgraph.state import AgentState

# Import Nodes
from app.langgraph.nodes.validate_session import validate_session_node
from app.langgraph.nodes.load_memory import load_memory_node
from app.langgraph.nodes.fetch_crm import fetch_crm_node
from app.langgraph.nodes.check_context import check_context_node
from app.langgraph.nodes.call_llm import call_llm_node
from app.langgraph.nodes.execute_action import execute_action_node
from app.langgraph.nodes.save_memory import save_memory_node

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("validate_session", validate_session_node)
workflow.add_node("load_memory", load_memory_node)
workflow.add_node("fetch_crm", fetch_crm_node)
workflow.add_node("check_context", check_context_node)
workflow.add_node("call_llm", call_llm_node)
workflow.add_node("execute_action", execute_action_node)
workflow.add_node("save_memory", save_memory_node)

# Set Entry Point
workflow.set_entry_point("validate_session")

# Edge: Validate Session -> Load Memory (or End)
def route_after_validation(state: AgentState):
    if state.get("response"): # Error occurred
        return "save_memory"
    return "load_memory"

workflow.add_conditional_edges(
    "validate_session",
    route_after_validation,
    {
        "save_memory": "save_memory",
        "load_memory": "load_memory"
    }
)

# Edge: Load Memory -> Fetch CRM (or Check Context for greetings)
def route_after_memory(state: AgentState):
    """
    Routes after loading memory.
    - Greetings: Skip to check_context (which will return greeting response)
    - All other queries: Route to fetch_crm
    """
    # If response already set (greeting handled in load_memory), route to check_context
    if state.get("response"):
        return "check_context"
    
    # All other queries route to CRM
    return "fetch_crm"

workflow.add_conditional_edges(
    "load_memory",
    route_after_memory,
    {
        "fetch_crm": "fetch_crm",
        "check_context": "check_context"
    }
)

# Edge: Fetch CRM -> Check Context
workflow.add_edge("fetch_crm", "check_context")

# Edge: Check Context -> Call LLM or Save Memory (if empty/error)
def route_after_check(state: AgentState):
    if state.get("response"): # "No data found" or error set by check_context
        return "save_memory"
    return "call_llm"

workflow.add_conditional_edges(
    "check_context",
    route_after_check,
    {
        "save_memory": "save_memory",
        "call_llm": "call_llm"
    }
)

# Edge: Call LLM -> Execute Action (if tool calls) or Save Memory (if response)
def route_after_llm(state: AgentState):
    # If response already exists, go to save_memory (action results formatted or regular response)
    if state.get("response"):
        return "save_memory"
    
    tool_calls = state.get("tool_calls")
    requires_confirmation = state.get("requires_confirmation", False)
    
    # If confirmation required, go back to call_llm to get user confirmation
    if requires_confirmation:
        return "call_llm"
    
    # If tool calls exist and no response yet, execute them
    if tool_calls and len(tool_calls) > 0:
        return "execute_action"
    
    # Otherwise, save memory and end
    return "save_memory"

workflow.add_conditional_edges(
    "call_llm",
    route_after_llm,
    {
        "execute_action": "execute_action",
        "call_llm": "call_llm",
        "save_memory": "save_memory"
    }
)

# Edge: Execute Action -> Call LLM (to format results)
workflow.add_edge("execute_action", "call_llm")

# Fallback node removed as it was unreachable
# workflow.add_edge("fallback", "save_memory")

# Edge: Save Memory -> END
workflow.add_edge("save_memory", END)

# Compile
graph = workflow.compile()
