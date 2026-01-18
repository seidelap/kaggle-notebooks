"""Tools available to Project Huddles."""

from typing import Any, Dict, Optional
import uuid

from dynamic_bot_org_chart.tools.base import Tool, ToolResult
from dynamic_bot_org_chart.integration.claude_code import ClaudeCodeManager
from dynamic_bot_org_chart.judges.llm_judge import LLMJudge
from dynamic_bot_org_chart.core.states import TaskState, HuddleState


class CreateTaskTool(Tool):
    """Tool for creating a Claude Code session (task)."""

    def __init__(self, claude_code_manager: ClaudeCodeManager, project_huddle):
        super().__init__(
            name="createTask",
            description="Creates a Claude Code session (task)"
        )
        self.claude_code_manager = claude_code_manager
        self.project_huddle = project_huddle

    async def execute(
        self,
        description: str,
        test_requirements: str,
        execution_timeout: Optional[int] = None,
        codebase_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """Create a new task."""
        try:
            # Generate task ID
            task_id = f"task-{uuid.uuid4().hex[:8]}"

            print(f"[{self.project_huddle.huddle_id}] Creating task: {task_id}")

            # Create Claude Code session
            session = await self.claude_code_manager.create_task(
                task_id=task_id,
                project_id=self.project_huddle.huddle_id,
                description=description,
                test_requirements=test_requirements,
                execution_timeout=execution_timeout,
                codebase_context=codebase_context
            )

            # Add to project's tasks
            self.project_huddle.tasks[task_id] = session

            return ToolResult(
                success=True,
                data={
                    "task_id": task_id,
                    "description": description,
                    "test_requirements": test_requirements
                },
                message=f"Task {task_id} created successfully"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to create task: {e}"
            )


class CancelTaskTool(Tool):
    """Tool for cancelling a Claude Code session (task)."""

    def __init__(self, claude_code_manager: ClaudeCodeManager, project_huddle):
        super().__init__(
            name="cancelTask",
            description="Cancels a Claude Code session (task)"
        )
        self.claude_code_manager = claude_code_manager
        self.project_huddle = project_huddle

    async def execute(self, task_id: str, **kwargs) -> ToolResult:
        """Cancel a task."""
        try:
            task = self.project_huddle.tasks.get(task_id)
            if not task:
                return ToolResult(
                    success=False,
                    error="Task not found",
                    message=f"Task {task_id} not found"
                )

            print(f"[{self.project_huddle.huddle_id}] Cancelling task: {task_id}")

            # Cancel the Claude Code session
            success = await self.claude_code_manager.cancel_task(task_id)

            if success:
                return ToolResult(
                    success=True,
                    data={"task_id": task_id},
                    message=f"Task {task_id} cancelled successfully"
                )
            else:
                return ToolResult(
                    success=False,
                    error="Failed to cancel task",
                    message=f"Failed to cancel task {task_id}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to cancel task: {e}"
            )


class CompleteProjectTool(Tool):
    """Tool for completing a project with artifact and evaluation."""

    def __init__(self, llm_judge: LLMJudge, project_huddle):
        super().__init__(
            name="completeProject",
            description="Completes project with artifact and LLM judge evaluation"
        )
        self.llm_judge = llm_judge
        self.project_huddle = project_huddle

    async def execute(
        self,
        artifact: Any,
        requirements: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Complete the project with artifact evaluation."""
        try:
            print(f"[{self.project_huddle.huddle_id}] Completing project with artifact")

            # Get completed tasks
            completed_tasks = [
                task for task in self.project_huddle.tasks.values()
                if task.context.state == TaskState.COMPLETED
            ]

            # Use LLM judge to evaluate artifact
            evaluation = await self.llm_judge.evaluate(
                artifact=artifact,
                requirements=requirements or self.project_huddle.description,
                artifact_specification=self.project_huddle.artifact_specification,
                context={
                    'task_results': [task.context.artifact for task in completed_tasks],
                    'project_description': self.project_huddle.description
                }
            )

            if evaluation.approved:
                print(f"[{self.project_huddle.huddle_id}] Artifact approved (score: {evaluation.score})")

                # Transition to COMPLETED
                self.project_huddle.context.transition_to(HuddleState.COMPLETED)
                self.project_huddle.context.artifact = artifact

                return ToolResult(
                    success=True,
                    data={
                        "artifact": artifact,
                        "evaluation": {
                            "score": evaluation.score,
                            "reasoning": evaluation.reasoning,
                            "approved": evaluation.approved
                        }
                    },
                    message=f"Project completed successfully (score: {evaluation.score})"
                )
            else:
                print(f"[{self.project_huddle.huddle_id}] Artifact not approved (score: {evaluation.score})")

                return ToolResult(
                    success=False,
                    error="Artifact evaluation failed",
                    data={
                        "evaluation": {
                            "score": evaluation.score,
                            "reasoning": evaluation.reasoning,
                            "feedback": evaluation.feedback,
                            "approved": evaluation.approved
                        }
                    },
                    message=f"Artifact not approved: {evaluation.feedback}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to complete project: {e}"
            )
