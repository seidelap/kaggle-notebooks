"""MCP tools for CEO Product Huddle."""

from typing import Any, Dict


def request_human_feedback_tool() -> Dict[str, Any]:
    """MCP tool definition for requesting human feedback (CEO only)."""
    return {
        "name": "requestHumanFeedback",
        "description": "Request feedback from a human (CEO special permission)",
        "input_schema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "The feedback request or question for the human"
                },
                "context": {
                    "type": "object",
                    "description": "Optional context to help the human understand the request"
                }
            },
            "required": ["request"]
        }
    }


# Tool execution function

async def execute_request_human_feedback(
    request: str,
    context_data: Dict[str, Any] = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute human feedback request."""
    huddle_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    feedback_request = {
        "huddle_id": huddle_id,
        "request": request,
        "context": context_data or {},
        "status": "PENDING"
    }

    shared_state.human_feedback_requests.append(feedback_request)

    # In production, this would pause execution and wait for human input
    # For now, we'll return a simulated response
    print("\n" + "=" * 60)
    print("HUMAN FEEDBACK REQUEST")
    print("=" * 60)
    print(f"From: {huddle_id}")
    print(f"Request: {request}")
    if context_data:
        print(f"Context: {context_data}")
    print("=" * 60)
    print("(In production, system would pause and wait for human response)")
    print("=" * 60)

    # Simulated response
    simulated_response = "Proceed with the plan as proposed."

    return {
        "success": True,
        "message": "Human feedback received",
        "human_response": simulated_response,
        "request": request
    }
