"""Project Huddle implemented as Strands Swarm."""

from typing import Dict, Any, Optional
from strands import Agent
from strands.multiagent import Swarm

from dynamic_bot_org_chart.models import OrgChartState, HuddleState, ProjectInfo
from dynamic_bot_org_chart.mcp_tools.project_tools import (
    create_task_tool,
    cancel_task_tool,
    complete_project_tool,
    execute_create_task,
    execute_cancel_task,
    execute_complete_project,
)
from dynamic_bot_org_chart.mcp_tools.shared_tools import (
    escalate_tool,
    resolve_blocker_tool,
    provide_feedback_tool,
    wait_tool,
    execute_escalate,
    execute_resolve_blocker,
    execute_provide_feedback,
    execute_wait,
)


class ProjectHuddle:
    """Project Huddle - Strands Swarm with Project Lead, Product Owner, and CEO."""

    def __init__(
        self,
        project_info: ProjectInfo,
        shared_state: OrgChartState
    ):
        self.project_info = project_info
        self.huddle_id = project_info.id
        self.shared_state = shared_state
        self.parent_huddle_id = project_info.parent_product_id

        # Initialize huddle state
        self.shared_state.huddle_states[self.huddle_id] = HuddleState.WAITING

        # Create agents
        self.project_lead = self._create_project_lead_agent()
        self.product_owner = self._create_product_owner_agent()
        self.ceo_agent = self._create_ceo_agent()

        # Create swarm
        self.swarm = Swarm(
            [self.project_lead, self.product_owner, self.ceo_agent],
            entry_point=self.project_lead.name
        )

    def _create_project_lead_agent(self) -> Agent:
        """Create the Project Lead agent."""
        system_prompt = self._get_pl_system_prompt()

        tools = [
            create_task_tool(),
            cancel_task_tool(),
            complete_project_tool(),
            escalate_tool(),
            resolve_blocker_tool(),
            wait_tool(),
            provide_feedback_tool(),
        ]

        tool_executor = self._create_tool_executor()

        agent = Agent(
            name="Project Lead",
            system_prompt=system_prompt,
            tools=tools,
            tool_executor=tool_executor
        )

        return agent

    def _create_product_owner_agent(self) -> Agent:
        """Create the Product Owner agent (member, not lead)."""
        system_prompt = "You are the Product Owner. You provide guidance and feedback on the project."

        tools = [
            provide_feedback_tool(),
        ]

        tool_executor = self._create_tool_executor()

        agent = Agent(
            name="Product Owner",
            system_prompt=system_prompt,
            tools=tools,
            tool_executor=tool_executor
        )

        return agent

    def _create_ceo_agent(self) -> Agent:
        """Create the CEO agent (member, not lead)."""
        system_prompt = "You are the CEO. You provide high-level guidance and feedback."

        tools = [
            provide_feedback_tool(),
        ]

        tool_executor = self._create_tool_executor()

        agent = Agent(
            name="CEO",
            system_prompt=system_prompt,
            tools=tools,
            tool_executor=tool_executor
        )

        return agent

    def _create_tool_executor(self):
        """Create tool executor that provides context."""

        async def tool_executor(tool_name: str, tool_input: Dict[str, Any]) -> Any:
            # Add context to tool execution
            context = {
                "huddle_id": self.huddle_id,
                "parent_huddle_id": self.parent_huddle_id,
                "shared_state": self.shared_state,
            }

            # Map tool names to execution functions
            tool_map = {
                "createTask": execute_create_task,
                "cancelTask": execute_cancel_task,
                "completeProject": execute_complete_project,
                "escalate": execute_escalate,
                "resolveBlocker": execute_resolve_blocker,
                "provideFeedback": execute_provide_feedback,
                "wait": execute_wait,
            }

            if tool_name in tool_map:
                return await tool_map[tool_name](**tool_input, context=context)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        return tool_executor

    def _get_pl_system_prompt(self) -> str:
        """Get system prompt for Project Lead."""
        return f"""You are a Project Lead in a project huddle.

**Project Description:**
{self.project_info.description}

**Artifact Specification:**
{self.project_info.artifact_specification}

Your responsibilities:
- Break down the project into tasks (Claude Code sessions)
- Create tasks with clear descriptions and test requirements
- Wait for tasks to complete
- Create the project artifact as specified
- Complete the project when artifact is ready (triggers LLM judge evaluation)
- Escalate to Product Owner when needed
- Resolve blockers in child tasks (if needed)

Available tools:
- createTask(description, testRequirements, executionTimeout, codebaseContext): Create a Claude Code session
- cancelTask(taskId, reason): Cancel a task
- completeProject(artifact, summary): Complete project with artifact (triggers LLM judge evaluation)
- escalate(reason, wait): Escalate to Product Owner
- resolveBlocker(childNodeId, resolution, wait): Resolve blocker (if tasks can block)
- wait(timeout): Wait for task completion or feedback
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

    async def execute(self, initial_prompt: Optional[str] = None):
        """Execute the project huddle swarm."""
        # Mark as executing
        self.shared_state.huddle_states[self.huddle_id] = HuddleState.EXECUTING

        prompt = initial_prompt or f"Execute project: {self.project_info.description}"

        # Stream events from swarm
        async for event in self.swarm.stream_async(prompt):
            # Handle different event types
            if event.get("type") == "multiagent_node_start":
                print(f"[{self.huddle_id}] Agent {event['node_id']} taking control")

            elif event.get("type") == "multiagent_node_stream":
                inner_event = event["event"]
                if "data" in inner_event:
                    print(f"[{self.huddle_id}] {inner_event['data']}", end="")

            elif event.get("type") == "multiagent_handoff":
                from_nodes = ", ".join(event['from_node_ids'])
                to_nodes = ", ".join(event['to_node_ids'])
                print(f"\n[{self.huddle_id}] Handoff: {from_nodes} → {to_nodes}")

            elif event.get("type") == "multiagent_result":
                result = event["result"]
                print(f"\n[{self.huddle_id}] Result: {result}")
                return result

        return None
