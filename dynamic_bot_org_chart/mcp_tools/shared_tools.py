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
    from dynamic_bot_org_chart.models import EscalationInfo, HuddleState

    huddle_id = context.get("huddle_id")
    parent_id = context.get("parent_huddle_id")

    if not parent_id:
        return {
            "success": False,
            "error": f"Huddle {huddle_id} has no parent to escalate to"
        }

    shared_state = context.get("shared_state")

    # Create escalation info
    escalation = EscalationInfo(
        from_huddle=huddle_id,
        to_huddle=parent_id,
        reason=reason,
        wait=wait
    )
    shared_state.escalations.append(escalation)

    # Mark this huddle as blocked
    shared_state.huddle_states[huddle_id] = HuddleState.BLOCKED

    return {
        "success": True,
        "message": f"Escalated to {parent_id}",
        "escalation": escalation.dict()
    }


async def execute_resolve_blocker(
    child_node_id: str,
    resolution: str,
    wait: bool = True,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute blocker resolution."""
    from dynamic_bot_org_chart.models import HuddleState
    from datetime import datetime

    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    # Check if child is blocked
    child_state = shared_state.huddle_states.get(child_node_id)
    if child_state != HuddleState.BLOCKED:
        return {
            "success": False,
            "error": f"Child {child_node_id} is not blocked (state: {child_state})"
        }

    # Find and resolve the escalation
    for escalation in shared_state.escalations:
        if escalation.from_huddle == child_node_id and escalation.resolved_at is None:
            escalation.resolution = resolution
            escalation.resolved_at = datetime.now()
            break

    # Unblock the child
    shared_state.huddle_states[child_node_id] = HuddleState.WAITING

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
    from dynamic_bot_org_chart.models import FeedbackInfo, HuddleState

    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    # Create feedback info
    feedback_entry = FeedbackInfo(
        from_huddle=huddle_id,
        to_huddle=target_huddle,
        feedback=feedback
    )
    shared_state.feedback.append(feedback_entry)

    # Wake up target if waiting
    target_state = shared_state.huddle_states.get(target_huddle)
    if target_state == HuddleState.WAITING:
        shared_state.huddle_states[target_huddle] = HuddleState.EXECUTING

    return {
        "success": True,
        "message": f"Feedback provided to {target_huddle}",
        "feedback": feedback_entry.dict()
    }


async def execute_wait(timeout: int = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute wait."""
    from dynamic_bot_org_chart.models import HuddleState

    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    # Mark as waiting
    shared_state.huddle_states[huddle_id] = HuddleState.WAITING

    return {
        "success": True,
        "message": f"Huddle {huddle_id} is now waiting",
        "timeout": timeout
    }
