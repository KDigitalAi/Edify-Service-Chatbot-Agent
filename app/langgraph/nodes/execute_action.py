from typing import Dict, Any, List, Optional
from app.langgraph.state import AgentState
from app.services.tool_registry import ToolRegistry
from app.db.audit_repo import AuditRepo
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

def execute_action_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes agentic actions (tool calls) from the LLM.
    Validates, executes, and returns results.
    Handles confirmation for destructive actions.
    """
    try:
        tool_calls = state.get("tool_calls")
        requires_confirmation = state.get("requires_confirmation", False)
        pending_action = state.get("pending_action")
        admin_id = state.get("admin_id", "anonymous")
        session_id = state.get("session_id")
        user_message = state.get("user_message", "")
        
        # If confirmation is required, check if user confirmed
        if requires_confirmation and pending_action:
            # Check if user message contains confirmation
            confirmation_keywords = ["yes", "confirm", "proceed", "delete", "ok", "okay", "yep", "sure"]
            user_msg_lower = user_message.lower().strip()
            
            is_confirmed = any(keyword in user_msg_lower for keyword in confirmation_keywords)
            
            if not is_confirmed:
                # User did not confirm, cancel action
                logger.info("Destructive action cancelled by user")
                
                # Clear pending action from database
                try:
                    from app.db.memory_repo import MemoryRepo
                    memory_repo = MemoryRepo()
                    memory_repo.clear_pending_action(session_id)
                except Exception as e:
                    logger.warning(f"Failed to clear pending action: {e}")
                
                return {
                    "action_results": [{
                        "tool_name": pending_action.get("tool_name"),
                        "status": "cancelled",
                        "message": "Action cancelled by user"
                    }],
                    "requires_confirmation": False,
                    "pending_action": None
                }
            
            # User confirmed, execute the pending action
            tool_name = pending_action["tool_name"]
            arguments = pending_action["arguments"]
            tool_calls = [{
                "name": tool_name,
                "arguments": arguments
            }]
            
            # Clear pending action from database after confirmation
            try:
                from app.db.memory_repo import MemoryRepo
                memory_repo = MemoryRepo()
                memory_repo.clear_pending_action(session_id)
                logger.info(f"Cleared pending action after confirmation for session {session_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to clear pending action: {e}")
            
            # Clear confirmation flags
            requires_confirmation = False
            pending_action = None
        
        # If no tool calls, skip execution
        if not tool_calls or len(tool_calls) == 0:
            return {}
        
        registry = ToolRegistry()
        audit_repo = AuditRepo()
        action_results = []
        
        # ENTITY MEMORY: Extract entity memory from state for auto-filling missing IDs
        # Generic approach - works for ALL CRM entities
        last_entity_type = state.get("last_entity_type")
        last_entity_id = state.get("last_entity_id")
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            
            if not tool_name:
                continue
            
            # ENTITY RESOLUTION: Auto-fill missing entity IDs from memory
            # Generic - works for any update/delete operation
            if "update_" in tool_name or "delete_" in tool_name:
                entity_type = tool_name.replace("update_", "").replace("delete_", "")
                entity_id_param = f"{entity_type}_id"
                
                # If entity_id is missing but we have matching entity in memory, auto-fill
                if (entity_id_param not in arguments or not arguments.get(entity_id_param)):
                    # Check if this tool matches the last entity type
                    if last_entity_type == entity_type and last_entity_id:
                        arguments[entity_id_param] = last_entity_id
                        logger.info(f"Auto-filled {entity_id_param} from memory: {last_entity_id} (last {entity_type})")
                    # Also check entity-specific memory keys for backward compatibility
                    elif f"last_{entity_type}_id" in state and state[f"last_{entity_type}_id"]:
                        arguments[entity_id_param] = state[f"last_{entity_type}_id"]
                        logger.info(f"Auto-filled {entity_id_param} from memory: {state[f'last_{entity_type}_id']}")
            
            # Validate tool call
            is_valid, error_msg = registry.validate_tool_call(tool_name, arguments)
            if not is_valid:
                logger.warning(f"Invalid tool call: {tool_name} - {error_msg}")
                action_results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "error": error_msg
                })
                # Audit log validation failure
                try:
                    audit_repo.log_action(
                        admin_id=admin_id,
                        action="tool_call_validation_failed",
                        details={
                            "tool_name": tool_name,
                            "error": error_msg,
                            "arguments": arguments
                        },
                        session_id=session_id
                    )
                except:
                    pass
                continue
            
            # Check if destructive action requires confirmation
            if registry.is_destructive_action(tool_name) and not requires_confirmation:
                logger.info(f"Destructive action {tool_name} requires confirmation")
                
                # Persist pending action to database for cross-request continuity
                try:
                    from app.db.memory_repo import MemoryRepo
                    memory_repo = MemoryRepo()
                    memory_repo.save_pending_action(
                        session_id=session_id,
                        tool_name=tool_name,
                        arguments=arguments
                    )
                    logger.info(f"Persisted pending action: {tool_name} for session {session_id[:8]}...")
                except Exception as mem_error:
                    logger.warning(f"Failed to persist pending action: {mem_error}")
                
                return {
                    "requires_confirmation": True,
                    "pending_action": {
                        "tool_name": tool_name,
                        "arguments": arguments
                    },
                    "response": f"I'm about to {tool_name.replace('_', ' ')}. This action cannot be undone. Please confirm by saying 'yes' or 'confirm' to proceed."
                }
            
            # Execute the tool
            try:
                tool_function = registry.get_tool_function(tool_name)
                if not tool_function:
                    raise ValueError(f"Tool function not found: {tool_name}")
                
                # Execute the function (all CRMRepo methods are sync)
                logger.info(f"Executing tool function: {tool_name} with arguments: {arguments}")
                result = tool_function(arguments)
                logger.info(f"Tool function returned: type={type(result)}, value={result if not isinstance(result, dict) or 'id' not in result else {'id': result.get('id'), 'type': 'dict'}}")
                
                # CRITICAL: Validate result structure to prevent false success
                # For CREATE/UPDATE operations: result must be a dict with "id"
                # For DELETE operations: result must be True (boolean)
                # For boolean results (delete operations), accept True as success
                if isinstance(result, bool):
                    if result is True:
                        action_results.append({
                            "tool_name": tool_name,
                            "status": "success",
                            "result": {"deleted": True}
                        })
                        logger.info(f"Successfully executed {tool_name}")
                        
                        # ENTITY MEMORY: Extract entity info for delete operations
                        # For delete, entity_id comes from arguments, not result
                        if "delete_" in tool_name:
                            entity_type = tool_name.replace("delete_", "")
                            entity_id_param = f"{entity_type}_id"
                            entity_id = arguments.get(entity_id_param)
                            
                            if entity_id:
                                entity_info = {
                                    "last_entity_type": entity_type,
                                    "last_entity_id": str(entity_id),
                                    f"last_{entity_type}_id": str(entity_id)
                                }
                                
                                # Persist entity memory to database
                                try:
                                    from app.db.memory_repo import MemoryRepo
                                    memory_repo = MemoryRepo()
                                    memory_repo.save_entity_memory(
                                        session_id=session_id,
                                        entity_type=entity_type,
                                        entity_id=str(entity_id),
                                        action="delete"
                                    )
                                    logger.info(f"Persisted entity memory: {entity_type} {entity_id} (delete)")
                                except Exception as mem_error:
                                    logger.warning(f"Failed to persist entity memory: {mem_error}")
                                
                                # Store in action_results for current request
                                action_results[-1]["entity_memory"] = entity_info
                    else:
                        action_results.append({
                            "tool_name": tool_name,
                            "status": "error",
                            "error": "Action returned False (operation failed)"
                        })
                        logger.warning(f"Tool {tool_name} returned False")
                # For dict results (create/update operations), validate structure
                elif isinstance(result, dict):
                    # CRITICAL: Must contain "id" to confirm database persistence
                    if "id" not in result or not result.get("id"):
                        error_msg = f"Action returned invalid result: missing 'id' field (database persistence not confirmed)"
                        logger.error(error_msg)
                        action_results.append({
                            "tool_name": tool_name,
                            "status": "error",
                            "error": error_msg
                        })
                    else:
                        # Valid result with confirmed ID
                        action_results.append({
                            "tool_name": tool_name,
                            "status": "success",
                            "result": result
                        })
                        logger.info(f"Successfully executed {tool_name} (ID: {result.get('id')})")
                        
                        # Audit log successful action
                        try:
                            audit_repo.log_action(
                                admin_id=admin_id,
                                action=f"tool_executed_{tool_name}",
                                details={
                                    "tool_name": tool_name,
                                    "arguments": arguments,
                                    "result_id": result.get("id")
                                },
                                session_id=session_id
                            )
                        except:
                            pass
                        
                        # ENTITY MEMORY: Extract entity info for conversational continuity
                        # Generic extraction - works for ALL CRM tables
                        entity_info = {}
                        
                        # Extract entity_type from tool_name (e.g., "create_lead" -> "lead", "update_campaign" -> "campaign", "delete_task" -> "task")
                        # Works for create, update, AND delete operations
                        if "create_" in tool_name or "update_" in tool_name or "delete_" in tool_name:
                            # Generic entity type extraction
                            entity_type = tool_name.replace("create_", "").replace("update_", "").replace("delete_", "")
                            
                            # Get entity_id from result
                            entity_id = result.get("id")
                            
                            # Generic entity name extraction - try common name fields
                            entity_name = (
                                result.get("name") or 
                                result.get("campaign_name") or 
                                result.get("trainer_name") or 
                                result.get("learner_name") or
                                result.get("title") or 
                                result.get("subject") or
                                result.get("email") or
                                None
                            )
                            
                            if entity_id:
                                entity_info[f"last_{entity_type}_id"] = str(entity_id)
                                entity_info["last_entity_type"] = entity_type
                                entity_info["last_entity_id"] = str(entity_id)
                            
                            if entity_name:
                                entity_info[f"last_{entity_type}_name"] = entity_name
                                entity_info["last_entity_name"] = entity_name
                            
                            # Determine action type
                            if "create_" in tool_name:
                                action = "create"
                            elif "update_" in tool_name:
                                action = "update"
                            elif "delete_" in tool_name:
                                action = "delete"
                            else:
                                action = "read"
                            
                            # Persist entity memory to database for cross-request continuity
                            if entity_id:
                                try:
                                    from app.db.memory_repo import MemoryRepo
                                    memory_repo = MemoryRepo()
                                    memory_repo.save_entity_memory(
                                        session_id=session_id,
                                        entity_type=entity_type,
                                        entity_id=str(entity_id),
                                        action=action,
                                        entity_name=entity_name
                                    )
                                    logger.info(f"Persisted entity memory: {entity_type} {entity_id} ({action})")
                                except Exception as mem_error:
                                    logger.warning(f"Failed to persist entity memory: {mem_error}")
                        
                        # Store entity info in action_results for state update (current request)
                        if entity_info:
                            action_results[-1]["entity_memory"] = entity_info
                else:
                    # Invalid result type
                    error_msg = f"Action returned invalid result type: {type(result)} (expected dict with 'id' or bool)"
                    logger.error(error_msg)
                    action_results.append({
                        "tool_name": tool_name,
                        "status": "error",
                        "error": error_msg
                    })
                    
            except Exception as e:
                # CRITICAL: Log full exception details for debugging
                error_msg = str(e)
                logger.error(f"Error executing tool {tool_name}: {error_msg}", exc_info=True)
                logger.error(f"Exception type: {type(e).__name__}")
                
                # Extract detailed error information
                if hasattr(e, 'args') and e.args:
                    logger.error(f"Exception args: {e.args}")
                
                # Propagate real database errors (never fabricate success)
                action_results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "error": error_msg  # Real error from database, not fabricated
                })
                
                # Audit log execution error
                try:
                    audit_repo.log_action(
                        admin_id=admin_id,
                        action="tool_execution_error",
                        details={
                            "tool_name": tool_name,
                            "error": str(e),
                            "arguments": arguments
                        },
                        session_id=session_id
                    )
                except:
                    pass
        
        # Extract entity memory from action results
        entity_memory = {}
        for result in action_results:
            if result.get("status") == "success" and "entity_memory" in result:
                entity_memory.update(result["entity_memory"])
        
        # Clear pending_action flag if actions completed successfully
        # This ensures pending_action is cleared after execution
        final_pending_action = None
        final_requires_confirmation = False
        
        # If we executed actions (not just checking confirmation), clear pending_action
        if action_results and len(action_results) > 0:
            # Check if all actions completed (success, error, or cancelled)
            all_completed = all(
                result.get("status") in ["success", "error", "cancelled"]
                for result in action_results
            )
            if all_completed:
                final_pending_action = None
                final_requires_confirmation = False
        
        return {
            "action_results": action_results,
            "requires_confirmation": final_requires_confirmation,
            "pending_action": final_pending_action,
            "tool_calls": None,  # Clear tool_calls after execution to prevent recursion
            **entity_memory  # Inject entity memory into state
        }
        
    except Exception as e:
        logger.error(f"Error in execute_action_node: {e}", exc_info=True)
        return {
            "action_results": [{
                "status": "error",
                "error": f"Execution error: {str(e)}"
            }]
        }

