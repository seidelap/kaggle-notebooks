"""Product Huddle implemented as Strands Swarm."""

from typing import Dict, Any, Optional
from strands import Agent
from strands.multiagent import Swarm

from dynamic_bot_org_chart.models import OrgChartState, HuddleState
from dynamic_bot_org_chart.mcp_tools.product_tools import (
    create_project_tool,
    cancel_project_tool,
    evaluate_completed_project_tool,
    execute_create_project,
    execute_cancel_project,
    execute_evaluate_completed_project,
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
from dynamic_bot_org_chart.mcp_tools.ceo_tools import (
    request_human_feedback_tool,
    execute_request_human_feedback,
)


class ProductHuddle:
    """Product Huddle - Strands Swarm with Product Owner and CEO."""

    def __init__(
        self,
        huddle_id: str,
        shared_state: OrgChartState,
        parent_huddle_id: Optional[str] = None,
        is_ceo: bool = False
    ):
        self.huddle_id = huddle_id
        self.shared_state = shared_state
        self.parent_huddle_id = parent_huddle_id
        self.is_ceo = is_ceo

        # Initialize huddle state
        self.shared_state.huddle_states[huddle_id] = HuddleState.WAITING

        # Create agents
        self.product_owner = self._create_product_owner_agent()
        self.ceo_agent = None if is_ceo else self._create_ceo_agent()

        # Create swarm
        agents = [self.product_owner]
        if self.ceo_agent:
            agents.append(self.ceo_agent)

        self.swarm = Swarm(agents, entry_point=self.product_owner.name)

    def _create_product_owner_agent(self) -> Agent:
        """Create the Product Owner agent."""
        system_prompt = self._get_po_system_prompt()

        # Define available tools
        tools = [
            create_project_tool(),
            cancel_project_tool(),
            evaluate_completed_project_tool(),
            resolve_blocker_tool(),
            wait_tool(),
            provide_feedback_tool(),
        ]

        # Add escalate tool if not CEO
        if not self.is_ceo:
            tools.append(escalate_tool())

        # Add human feedback tool if CEO
        if self.is_ceo:
            tools.append(request_human_feedback_tool())

        # Create tool execution map
        tool_executor = self._create_tool_executor()

        agent = Agent(
            name="Product Owner" if not self.is_ceo else "CEO",
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
                "createProject": execute_create_project,
                "cancelProject": execute_cancel_project,
                "evaluateCompletedProject": execute_evaluate_completed_project,
                "escalate": execute_escalate,
                "resolveBlocker": execute_resolve_blocker,
                "provideFeedback": execute_provide_feedback,
                "wait": execute_wait,
                "requestHumanFeedback": execute_request_human_feedback,
            }

            if tool_name in tool_map:
                return await tool_map[tool_name](**tool_input, context=context)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        return tool_executor

    def _get_po_system_prompt(self) -> str:
        """Get system prompt for Product Owner."""
        if self.is_ceo:
            return """You are the CEO in the CEO product huddle.

Your responsibilities:
- Manage the top-level product
- Create projects to develop features or fix issues
- Evaluate completed projects
- Decide whether to convert completed projects to new products or keep as part of parent product
- Request human feedback when needed (special permission)
- Resolve blockers in child projects

Available tools:
- createProject(description, artifactSpecification, executionTimeout): Create a new project
- cancelProject(projectId, reason): Cancel a project
- evaluateCompletedProject(projectId, convert_to_product): Evaluate a completed project
- resolveBlocker(childNodeId, resolution, wait): Resolve blocker in child project
- wait(timeout): Wait for project completion or feedback
- provideFeedback(targetHuddle, feedback): Provide feedback to another huddle
- requestHumanFeedback(request, context): Request feedback from a human (CEO special permission)

Guidelines:
- Create projects with clear artifact specifications
- Wait for projects to complete before evaluating
- Request human feedback when critical decisions need to be made
- Resolve blockers when child projects need help
- You are the final decision maker
"""
        else:
            return """You are a Product Owner in a product huddle.

Your responsibilities:
- Manage the product
- Create projects to develop features or fix issues
- Evaluate completed projects
- Decide whether to convert completed projects to new products or keep as part of parent product
- Escalate to CEO when needed
- Resolve blockers in child projects

Available tools:
- createProject(description, artifactSpecification, executionTimeout): Create a new project
- cancelProject(projectId, reason): Cancel a project
- evaluateCompletedProject(projectId, convert_to_product): Evaluate a completed project
- escalate(reason, wait): Escalate to CEO
- resolveBlocker(childNodeId, resolution, wait): Resolve blocker in child project
- wait(timeout): Wait for project completion or feedback
- provideFeedback(targetHuddle, feedback): Provide feedback to another huddle

Guidelines:
- Create projects with clear artifact specifications
- Wait for projects to complete before evaluating
- Escalate when you need guidance or are blocked
- Resolve blockers when child projects need help
"""

    async def execute(self, initial_prompt: Optional[str] = None):
        """Execute the product huddle swarm."""
        # Mark as executing
        self.shared_state.huddle_states[self.huddle_id] = HuddleState.EXECUTING

        prompt = initial_prompt or f"Manage product {self.huddle_id}"

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
