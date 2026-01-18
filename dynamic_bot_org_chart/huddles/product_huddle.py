"""Product Huddle implementation."""

from typing import Optional
from dynamic_bot_org_chart.huddles.base import BaseHuddle, HuddleMember, MemberRole
from dynamic_bot_org_chart.core.events import EventBus
from dynamic_bot_org_chart.core.graph import Graph
from dynamic_bot_org_chart.tools.product_tools import (
    CreateProjectTool,
    CancelProjectTool,
    EvaluateCompletedProjectTool,
)
from dynamic_bot_org_chart.tools.shared_tools import (
    EscalateTool,
    ResolveBlockerTool,
    ProvideFeedbackTool,
    WaitTool,
)
from dynamic_bot_org_chart.tools.ceo_tools import RequestHumanFeedbackTool


class ProductHuddle(BaseHuddle):
    """Product Huddle - manages products and creates projects."""

    def __init__(
        self,
        huddle_id: str,
        event_bus: EventBus,
        graph: Graph,
        parent_huddle_id: Optional[str] = None,
        is_ceo: bool = False
    ):
        # Create members
        tools_list = [
            "createProject",
            "cancelProject",
            "evaluateCompletedProject",
            "escalate",
            "resolveBlocker",
            "wait",
            "provideFeedback"
        ]

        # Add requestHumanFeedback for CEO
        if is_ceo:
            tools_list.append("requestHumanFeedback")

        members = [
            HuddleMember(
                member_id=f"{huddle_id}-po",
                name="Product Owner" if not is_ceo else "CEO",
                role=MemberRole.HUDDLE_LEAD,
                system_prompt=self._get_po_system_prompt(is_ceo),
                tools=tools_list
            ),
        ]

        # Add CEO if not the CEO huddle
        if not is_ceo:
            members.append(
                HuddleMember(
                    member_id="ceo",
                    name="CEO",
                    role=MemberRole.MEMBER,
                    system_prompt="You are the CEO. You provide high-level guidance.",
                    tools=["provideFeedback"]
                )
            )

        super().__init__(
            huddle_id=huddle_id,
            huddle_type="product",
            members=members,
            event_bus=event_bus,
            parent_huddle_id=parent_huddle_id
        )

        self.graph = graph
        self.is_ceo = is_ceo

        # Register tools (only huddle lead can use most tools)
        self.register_tool("createProject", CreateProjectTool(graph, self))
        self.register_tool("cancelProject", CancelProjectTool(graph, self))
        self.register_tool("evaluateCompletedProject", EvaluateCompletedProjectTool(graph, self))
        self.register_tool("escalate", EscalateTool(graph, self))
        self.register_tool("resolveBlocker", ResolveBlockerTool(graph, self))
        self.register_tool("provideFeedback", ProvideFeedbackTool(graph, self))
        self.register_tool("wait", WaitTool(self))

        # Add requestHumanFeedback for CEO
        if is_ceo:
            self.register_tool("requestHumanFeedback", RequestHumanFeedbackTool(self))

    def _get_po_system_prompt(self, is_ceo: bool = False) -> str:
        """Get system prompt for Product Owner or CEO."""
        if is_ceo:
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
- cancelProject(projectId): Cancel a project
- evaluateCompletedProject(projectId): Evaluate a completed project
- resolveBlocker(childNodeId, wait=True): Resolve blocker in child project
- wait(): Wait for project completion or feedback
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
- cancelProject(projectId): Cancel a project
- evaluateCompletedProject(projectId): Evaluate a completed project
- escalate(reason, wait=True): Escalate to CEO
- resolveBlocker(childNodeId, wait=True): Resolve blocker in child project
- wait(): Wait for project completion or feedback
- provideFeedback(targetHuddle, feedback): Provide feedback to another huddle

Guidelines:
- Create projects with clear artifact specifications
- Wait for projects to complete before evaluating
- Escalate when you need guidance or are blocked
- Resolve blockers when child projects need help
"""

    async def execute(self):
        """Execute the product huddle."""
        print(f"[{self.huddle_id}] Product Huddle executing...")

        # In a real implementation, this would use the Agent SDK to run the agents
        # For now, this is a placeholder that demonstrates the structure

        # Get context for LLM
        context = self.get_context_for_llm()

        print(f"[{self.huddle_id}] Context: {context}")

        # Placeholder for agent execution
        # In production, call Agent SDK here with:
        # - System prompt from huddle lead
        # - Context
        # - Available tools
        # - Event handlers

        return context
