"""Shared MCP tools available to all huddles."""

from typing import Any, Dict


def escalate_tool() -> Dict[str, Any]:
    """MCP tool definition for escalating to parent huddle."""
    return {
        "name": "escalate",
        "description": "Escalate an issue to the parent huddle (one level up)",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for escalation"
                },
                "wait": {
                    "type": "boolean",
                    "description": "Whether to wait for response (default: true)",
                    "default": True
                }
            },
            "required": ["reason"]
        }
    }


def resolve_blocker_tool() -> Dict[str, Any]:
    """MCP tool definition for resolving a blocker in a child node."""
    return {
        "name": "resolveBlocker",
        "description": "Resolve a blocker in a child node (huddle lead only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "child_node_id": {
                    "type": "string",
                    "description": "The ID of the child node that is blocked"
                },
                "resolution": {
                    "type": "string",
                    "description": "The resolution or guidance to unblock the child"
                },
                "wait": {
                    "type": "boolean",
                    "description": "Whether to wait after resolution (default: true)",
                    "default": True
                }
            },
            "required": ["child_node_id", "resolution"]
        }
    }


def provide_feedback_tool() -> Dict[str, Any]:
    """MCP tool definition for providing feedback to another huddle."""
    return {
        "name": "provideFeedback",
        "description": "Provide feedback to another huddle (can go up/down/across chain)",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_huddle": {
                    "type": "string",
                    "description": "The ID of the target huddle to receive feedback"
                },
                "feedback": {
                    "type": "string",
                    "description": "The feedback message"
                }
            },
            "required": ["target_huddle", "feedback"]
        }
    }


def wait_tool() -> Dict[str, Any]:
    """MCP tool definition for waiting until any child completes or feedback is provided."""
    return {
        "name": "wait",
        "description": "Wait until any child completes or feedback is provided",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds (default: no timeout)"
                }
            }
        }
    }


# Tool execution functions (called by Strands when tool is used)

async def execute_escalate(reason: str, wait: bool = True, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute escalation."""
    huddle_id = context.get("huddle_id")
    parent_id = context.get("parent_huddle_id")

    if not parent_id:
        return {
            "success": False,
            "error": f"Huddle {huddle_id} has no parent to escalate to"
        }

    # Get shared state from context
    shared_state = context.get("shared_state", {})

    # Add escalation to shared state
    if "escalations" not in shared_state:
        shared_state["escalations"] = []

    escalation = {
        "from": huddle_id,
        "to": parent_id,
        "reason": reason,
        "wait": wait
    }
    shared_state["escalations"].append(escalation)

    # Mark this huddle as blocked
    shared_state[f"{huddle_id}_state"] = "BLOCKED"
    shared_state[f"{huddle_id}_blocked_reason"] = reason

    return {
        "success": True,
        "message": f"Escalated to {parent_id}",
        "escalation": escalation
    }


async def execute_resolve_blocker(
    child_node_id: str,
    resolution: str,
    wait: bool = True,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute blocker resolution."""
    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state", {})

    # Check if child is blocked
    child_state = shared_state.get(f"{child_node_id}_state")
    if child_state != "BLOCKED":
        return {
            "success": False,
            "error": f"Child {child_node_id} is not blocked (state: {child_state})"
        }

    # Resolve the blocker
    shared_state[f"{child_node_id}_state"] = "WAITING"
    shared_state[f"{child_node_id}_blocked_reason"] = None
    shared_state[f"{child_node_id}_resolution"] = resolution

    # Add resolution to history
    if "resolutions" not in shared_state:
        shared_state["resolutions"] = []

    shared_state["resolutions"].append({
        "parent": huddle_id,
        "child": child_node_id,
        "resolution": resolution
    })

    return {
        "success": True,
        "message": f"Resolved blocker in {child_node_id}",
        "resolution": resolution
    }


async def execute_provide_feedback(
    target_huddle: str,
    feedback: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute providing feedback."""
    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state", {})

    # Add feedback to shared state
    if "feedback" not in shared_state:
        shared_state["feedback"] = []

    feedback_entry = {
        "from": huddle_id,
        "to": target_huddle,
        "feedback": feedback
    }
    shared_state["feedback"].append(feedback_entry)

    # Wake up target if waiting
    target_state = shared_state.get(f"{target_huddle}_state")
    if target_state == "WAITING":
        shared_state[f"{target_huddle}_state"] = "EXECUTING"

    return {
        "success": True,
        "message": f"Feedback provided to {target_huddle}",
        "feedback": feedback_entry
    }


async def execute_wait(timeout: int = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute wait."""
    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state", {})

    # Mark as waiting
    shared_state[f"{huddle_id}_state"] = "WAITING"

    return {
        "success": True,
        "message": f"Huddle {huddle_id} is now waiting",
        "timeout": timeout
    }
