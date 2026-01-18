"""MCP tools for Project Huddles."""

from typing import Any, Dict
import uuid


def create_task_tool() -> Dict[str, Any]:
    """MCP tool definition for creating a Claude Code session (task)."""
    return {
        "name": "createTask",
        "description": "Create a Claude Code session (task) for autonomous coding work (Project Lead only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the task"
                },
                "test_requirements": {
                    "type": "string",
                    "description": "Test requirements (TDD approach - tests must pass)"
                },
                "execution_timeout": {
                    "type": "number",
                    "description": "Optional execution timeout in seconds"
                },
                "codebase_context": {
                    "type": "object",
                    "description": "Optional codebase context (file paths, dependencies, etc.)"
                }
            },
            "required": ["description", "test_requirements"]
        }
    }


def cancel_task_tool() -> Dict[str, Any]:
    """MCP tool definition for cancelling a task."""
    return {
        "name": "cancelTask",
        "description": "Cancel a Claude Code session (task) (Project Lead only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to cancel"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for cancellation"
                }
            },
            "required": ["task_id"]
        }
    }


def complete_project_tool() -> Dict[str, Any]:
    """MCP tool definition for completing a project with artifact."""
    return {
        "name": "completeProject",
        "description": "Complete the project with artifact (triggers LLM judge evaluation) (Project Lead only)",
        "input_schema": {
            "type": "object",
            "properties": {
                "artifact": {
                    "type": "string",
                    "description": "The project artifact (as specified in artifact specification)"
                },
                "summary": {
                    "type": "string",
                    "description": "Optional summary of the project completion"
                }
            },
            "required": ["artifact"]
        }
    }


# Tool execution functions

async def execute_create_task(
    description: str,
    test_requirements: str,
    execution_timeout: int = None,
    codebase_context: Dict[str, Any] = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute task creation."""
    project_id = context.get("huddle_id")
    shared_state = context.get("shared_state", {})

    # Generate task ID
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # Add task to shared state
    if "tasks" not in shared_state:
        shared_state["tasks"] = {}

    task_data = {
        "id": task_id,
        "project_id": project_id,
        "description": description,
        "test_requirements": test_requirements,
        "execution_timeout": execution_timeout,
        "codebase_context": codebase_context or {},
        "state": "CREATED"
    }

    shared_state["tasks"][task_id] = task_data

    # Add to pending Agent SDK sessions list
    if "pending_agent_sessions" not in shared_state:
        shared_state["pending_agent_sessions"] = []

    shared_state["pending_agent_sessions"].append({
        "task_id": task_id,
        "project_id": project_id,
        "data": task_data
    })

    return {
        "success": True,
        "task_id": task_id,
        "message": f"Task {task_id} created successfully"
    }


async def execute_cancel_task(
    task_id: str,
    reason: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute task cancellation."""
    shared_state = context.get("shared_state", {})

    tasks = shared_state.get("tasks", {})
    if task_id not in tasks:
        return {
            "success": False,
            "error": f"Task {task_id} not found"
        }

    # Update task state
    tasks[task_id]["state"] = "CANCELLED"
    tasks[task_id]["cancel_reason"] = reason

    return {
        "success": True,
        "message": f"Task {task_id} cancelled",
        "reason": reason
    }


async def execute_complete_project(
    artifact: str,
    summary: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute project completion."""
    project_id = context.get("huddle_id")
    shared_state = context.get("shared_state", {})

    projects = shared_state.get("projects", {})
    if project_id not in projects:
        return {
            "success": False,
            "error": f"Project {project_id} not found"
        }

    project = projects[project_id]

    # Get completed tasks
    tasks = shared_state.get("tasks", {})
    completed_tasks = [
        task for task in tasks.values()
        if task["project_id"] == project_id and task["state"] == "COMPLETED"
    ]

    # Prepare for LLM judge evaluation
    evaluation_request = {
        "project_id": project_id,
        "artifact": artifact,
        "requirements": project["description"],
        "artifact_specification": project["artifact_specification"],
        "completed_tasks": [
            {
                "task_id": task["id"],
                "description": task["description"],
                "artifact": task.get("artifact")
            }
            for task in completed_tasks
        ],
        "summary": summary
    }

    # Add to pending evaluations list
    if "pending_evaluations" not in shared_state:
        shared_state["pending_evaluations"] = []

    shared_state["pending_evaluations"].append(evaluation_request)

    # Update project state (will be finalized after LLM judge evaluation)
    project["state"] = "PENDING_EVALUATION"
    project["artifact"] = artifact
    project["summary"] = summary

    return {
        "success": True,
        "message": f"Project {project_id} submitted for evaluation",
        "evaluation_pending": True
    }
