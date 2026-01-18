"""MCP tools for Product Huddles."""

from typing import Any, Dict
import uuid


def create_project_tool() -> Dict[str, Any]:
    """MCP tool definition for creating a new project."""
    return {
        "name": "createProject",
        "description": "Create a new project with artifact specification (Product Owner only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the project"
                },
                "artifact_specification": {
                    "type": "string",
                    "description": "Specification for how the project artifact should be created/synthesized"
                },
                "execution_timeout": {
                    "type": "number",
                    "description": "Optional execution timeout in seconds"
                }
            },
            "required": ["description", "artifact_specification"]
        }
    }


def cancel_project_tool() -> Dict[str, Any]:
    """MCP tool definition for cancelling a project."""
    return {
        "name": "cancelProject",
        "description": "Cancel a project (Product Owner only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project to cancel"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for cancellation"
                }
            },
            "required": ["project_id"]
        }
    }


def evaluate_completed_project_tool() -> Dict[str, Any]:
    """MCP tool definition for evaluating a completed project."""
    return {
        "name": "evaluateCompletedProject",
        "description": "Evaluate a completed project and decide next action (Product Owner only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the completed project"
                },
                "convert_to_product": {
                    "type": "boolean",
                    "description": "Whether to convert the project to a new standalone product",
                    "default": False
                }
            },
            "required": ["project_id"]
        }
    }


# Tool execution functions

async def execute_create_project(
    description: str,
    artifact_specification: str,
    execution_timeout: int = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute project creation."""
    from dynamic_bot_org_chart.models import ProjectInfo, HuddleState

    product_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    # Generate project ID
    project_id = f"project-{uuid.uuid4().hex[:8]}"

    # Create project info using Pydantic model
    project_info = ProjectInfo(
        id=project_id,
        parent_product_id=product_id,
        description=description,
        artifact_specification=artifact_specification,
        execution_timeout=execution_timeout,
        state=HuddleState.WAITING
    )

    # Add to shared state
    shared_state.projects[project_id] = project_info

    # Add to graph nodes list (to be created later)
    shared_state.pending_graph_nodes.append({
        "type": "project",
        "id": project_id,
        "parent": product_id,
        "project_info": project_info
    })

    return {
        "success": True,
        "project_id": project_id,
        "message": f"Project {project_id} created successfully"
    }


async def execute_cancel_project(
    project_id: str,
    reason: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute project cancellation."""
    shared_state = context.get("shared_state", {})

    projects = shared_state.get("projects", {})
    if project_id not in projects:
        return {
            "success": False,
            "error": f"Project {project_id} not found"
        }

    # Update project state
    projects[project_id]["state"] = "CANCELLED"
    projects[project_id]["cancel_reason"] = reason

    return {
        "success": True,
        "message": f"Project {project_id} cancelled",
        "reason": reason
    }


async def execute_evaluate_completed_project(
    project_id: str,
    convert_to_product: bool = False,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute project evaluation."""
    shared_state = context.get("shared_state", {})

    projects = shared_state.get("projects", {})
    if project_id not in projects:
        return {
            "success": False,
            "error": f"Project {project_id} not found"
        }

    project = projects[project_id]
    if project["state"] != "COMPLETED":
        return {
            "success": False,
            "error": f"Project {project_id} is not completed (state: {project['state']})"
        }

    if convert_to_product:
        # Convert to new product
        new_product_id = f"product-{uuid.uuid4().hex[:8]}"

        if "products" not in shared_state:
            shared_state["products"] = {}

        shared_state["products"][new_product_id] = {
            "id": new_product_id,
            "original_project_id": project_id,
            "description": project["description"],
            "artifact": project.get("artifact"),
            "state": "ACTIVE"
        }

        action = "converted_to_product"
        result_data = {"new_product_id": new_product_id}
    else:
        # Keep as part of parent product
        action = "kept_in_parent_product"
        result_data = {"parent_product_id": project["parent_product_id"]}

    return {
        "success": True,
        "message": f"Project {project_id} evaluated: {action}",
        "action": action,
        **result_data
    }
