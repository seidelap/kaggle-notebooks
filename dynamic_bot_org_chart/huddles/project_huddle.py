"""Project Huddle implementation."""

from typing import Optional, Dict, Any
from dynamic_bot_org_chart.huddles.base import BaseHuddle, HuddleMember, MemberRole
from dynamic_bot_org_chart.core.events import EventBus
from dynamic_bot_org_chart.integration.claude_code import ClaudeCodeManager
from dynamic_bot_org_chart.judges.llm_judge import LLMJudge
from dynamic_bot_org_chart.tools.project_tools import (
    CreateTaskTool,
    CancelTaskTool,
    CompleteProjectTool,
)
from dynamic_bot_org_chart.tools.shared_tools import (
    EscalateTool,
    ResolveBlockerTool,
    ProvideFeedbackTool,
    WaitTool,
)


class ProjectHuddle(BaseHuddle):
    """Project Huddle - manages projects and creates tasks (Claude Code sessions)."""

    def __init__(
        self,
        huddle_id: str,
        event_bus: EventBus,
        parent_huddle_id: str,
        description: str,
        artifact_specification: str,
        execution_timeout: Optional[int] = None,
        claude_code_manager: Optional[ClaudeCodeManager] = None,
        llm_judge: Optional[LLMJudge] = None
    ):
        # Create members
        members = [
            HuddleMember(
                member_id=f"{huddle_id}-pl",
                name="Project Lead",
                role=MemberRole.HUDDLE_LEAD,
                system_prompt=self._get_pl_system_prompt(description, artifact_specification),
                tools=[
                    "createTask",
                    "cancelTask",
                    "completeProject",
                    "escalate",
                    "resolveBlocker",
                    "wait",
                    "provideFeedback"
                ]
            ),
            HuddleMember(
                member_id=f"{parent_huddle_id}-po",
                name="Product Owner",
                role=MemberRole.MEMBER,
                system_prompt="You are the Product Owner. You provide guidance and feedback.",
                tools=["provideFeedback"]
            ),
            HuddleMember(
                member_id="ceo",
                name="CEO",
                role=MemberRole.MEMBER,
                system_prompt="You are the CEO. You provide high-level guidance.",
                tools=["provideFeedback"]
            ),
        ]

        super().__init__(
            huddle_id=huddle_id,
            huddle_type="project",
            members=members,
            event_bus=event_bus,
            parent_huddle_id=parent_huddle_id
        )

        self.description = description
        self.artifact_specification = artifact_specification
        self.execution_timeout = execution_timeout

        # Tasks tracking (Claude Code sessions)
        self.tasks: Dict[str, Any] = {}

        # Managers
        self.claude_code_manager = claude_code_manager or ClaudeCodeManager()
        self.llm_judge = llm_judge or LLMJudge()

        # Register tools (only huddle lead can use most tools)
        self.register_tool("createTask", CreateTaskTool(self.claude_code_manager, self))
        self.register_tool("cancelTask", CancelTaskTool(self.claude_code_manager, self))
        self.register_tool("completeProject", CompleteProjectTool(self.llm_judge, self))
        self.register_tool("escalate", EscalateTool(None, self))  # No graph needed for project escalation
        self.register_tool("resolveBlocker", ResolveBlockerTool(None, self))
        self.register_tool("provideFeedback", ProvideFeedbackTool(None, self))
        self.register_tool("wait", WaitTool(self))

    def _get_pl_system_prompt(self, description: str, artifact_specification: str) -> str:
        """Get system prompt for Project Lead."""
        return f"""You are a Project Lead in a project huddle.

**Project Description:**
{description}

**Artifact Specification:**
{artifact_specification}

Your responsibilities:
- Break down the project into tasks (Claude Code sessions)
- Create tasks with clear descriptions and test requirements
- Wait for tasks to complete
- Create the project artifact as specified
- Use LLM judge to evaluate the artifact
- Complete the project when artifact is approved
- Escalate to Product Owner when needed
- Resolve blockers in child tasks (if needed)

Available tools:
- createTask(description, testRequirements, executionTimeout, codebaseContext): Create a Claude Code session
- cancelTask(taskId): Cancel a task
- completeProject(artifact, requirements): Complete project with artifact (triggers LLM judge evaluation)
- escalate(reason, wait=True): Escalate to Product Owner
- resolveBlocker(childNodeId, wait=True): Resolve blocker (if tasks can block)
- wait(): Wait for task completion or feedback
- provideFeedback(targetHuddle, feedback): Provide feedback to another huddle

Guidelines:
- Create tasks with clear test requirements (TDD approach)
- If any task is not immediately ready to start, do not start it - use wait() if another task is required first
- Wait for all tasks to complete before creating the project artifact
- Use the artifact specification to guide artifact creation
- The artifact should combine or synthesize task outputs
- Only call completeProject() when artifact is ready
- Escalate when you need requirements clarification or are blocked
"""

    async def execute(self):
        """Execute the project huddle."""
        print(f"[{self.huddle_id}] Project Huddle executing...")

        # In a real implementation, this would use the Agent SDK to run the agents
        # For now, this is a placeholder that demonstrates the structure

        # Get context for LLM
        context = self.get_context_for_llm()
        context.update({
            "description": self.description,
            "artifact_specification": self.artifact_specification,
            "tasks": {
                task_id: task.context.state.value
                for task_id, task in self.tasks.items()
            }
        })

        print(f"[{self.huddle_id}] Context: {context}")

        # Placeholder for agent execution
        # In production, call Agent SDK here with:
        # - System prompt from huddle lead
        # - Context
        # - Available tools
        # - Event handlers

        return context
