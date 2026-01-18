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
    from dynamic_bot_org_chart.models import TaskInfo, TaskState

    project_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    # Generate task ID
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # Create task info using Pydantic model
    task_info = TaskInfo(
        id=task_id,
        project_id=project_id,
        description=description,
        test_requirements=test_requirements,
        execution_timeout=execution_timeout,
        codebase_context=codebase_context or {},
        state=TaskState.PENDING
    )

    # Add to shared state
    shared_state.tasks[task_id] = task_info

    return {
        "success": True,
        "task_id": task_id,
        "message": f"Task {task_id} created successfully",
        "description": description
    }


async def execute_cancel_task(
    task_id: str,
    reason: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute task cancellation."""
    from dynamic_bot_org_chart.models import TaskState
    from datetime import datetime

    shared_state = context.get("shared_state")

    if task_id not in shared_state.tasks:
        return {
            "success": False,
            "error": f"Task {task_id} not found"
        }

    task = shared_state.tasks[task_id]
    task.state = TaskState.FAILED
    task.completed_at = datetime.now()

    return {
        "success": True,
        "message": f"Task {task_id} cancelled",
        "reason": reason
    }


async def execute_complete_project(
    artifact: Dict[str, Any],
    summary: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute project completion with LLM judge evaluation."""
    from dynamic_bot_org_chart.models import HuddleState, TaskState
    from datetime import datetime

    project_id = context.get("huddle_id")
    shared_state = context.get("shared_state")

    if project_id not in shared_state.projects:
        return {
            "success": False,
            "error": f"Project {project_id} not found"
        }

    project = shared_state.projects[project_id]

    # Get completed tasks
    completed_tasks = [
        task for task in shared_state.tasks.values()
        if task.project_id == project_id and task.state == TaskState.COMPLETED
    ]

    # In production, would call LLM judge here for evaluation
    # For now, we'll simulate approval
    evaluation_score = 0.85

    if evaluation_score >= 0.7:
        # Approved
        project.state = HuddleState.COMPLETED
        project.artifact = artifact
        project.completed_at = datetime.now()

        return {
            "success": True,
            "message": f"Project {project_id} completed successfully",
            "artifact": artifact,
            "evaluation_score": evaluation_score,
            "summary": summary
        }
    else:
        return {
            "success": False,
            "error": "Artifact evaluation failed",
            "evaluation_score": evaluation_score,
            "message": "Artifact did not meet requirements"
        }
