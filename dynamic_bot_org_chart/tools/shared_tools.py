"""Shared tools available to all huddles."""

from typing import Optional

from dynamic_bot_org_chart.tools.base import Tool, ToolResult
from dynamic_bot_org_chart.core.graph import Graph


class EscalateTool(Tool):
    """Tool for escalating to parent huddle."""

    def __init__(self, graph: Graph, huddle):
        super().__init__(
            name="escalate",
            description="Escalates to parent huddle"
        )
        self.graph = graph
        self.huddle = huddle

    async def execute(self, reason: str, wait: bool = True, **kwargs) -> ToolResult:
        """Escalate to parent huddle."""
        try:
            if not self.huddle.parent_huddle_id:
                return ToolResult(
                    success=False,
                    error="No parent huddle",
                    message=f"Huddle {self.huddle.huddle_id} has no parent to escalate to"
                )

            print(f"[{self.huddle.huddle_id}] Escalating to {self.huddle.parent_huddle_id}: {reason}")

            # Use huddle's escalate method
            await self.huddle.escalate(reason=reason, wait=wait)

            return ToolResult(
                success=True,
                data={
                    "parent_huddle_id": self.huddle.parent_huddle_id,
                    "reason": reason
                },
                message=f"Escalated to {self.huddle.parent_huddle_id}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to escalate: {e}"
            )


class ResolveBlockerTool(Tool):
    """Tool for resolving blocker in child node."""

    def __init__(self, graph: Graph, huddle):
        super().__init__(
            name="resolveBlocker",
            description="Resolves blocker in child node"
        )
        self.graph = graph
        self.huddle = huddle

    async def execute(self, child_node_id: str, wait: bool = True, **kwargs) -> ToolResult:
        """Resolve blocker in child node."""
        try:
            child = self.huddle.children.get(child_node_id)
            if not child:
                return ToolResult(
                    success=False,
                    error="Child not found",
                    message=f"Child {child_node_id} not found"
                )

            print(f"[{self.huddle.huddle_id}] Resolving blocker in {child_node_id}")

            # Use huddle's resolve_blocker method
            await self.huddle.resolve_blocker(child_node_id=child_node_id, wait=wait)

            return ToolResult(
                success=True,
                data={"child_node_id": child_node_id},
                message=f"Blocker resolved in {child_node_id}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to resolve blocker: {e}"
            )


class ProvideFeedbackTool(Tool):
    """Tool for providing feedback to another huddle."""

    def __init__(self, graph: Graph, huddle):
        super().__init__(
            name="provideFeedback",
            description="Provides feedback to another huddle"
        )
        self.graph = graph
        self.huddle = huddle

    async def execute(self, target_huddle: str, feedback: str, **kwargs) -> ToolResult:
        """Provide feedback to another huddle."""
        try:
            print(f"[{self.huddle.huddle_id}] Providing feedback to {target_huddle}")

            # Use huddle's provide_feedback method
            await self.huddle.provide_feedback(target_huddle=target_huddle, feedback=feedback)

            return ToolResult(
                success=True,
                data={
                    "target_huddle": target_huddle,
                    "feedback": feedback
                },
                message=f"Feedback provided to {target_huddle}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to provide feedback: {e}"
            )


class WaitTool(Tool):
    """Tool for waiting until any child completes or feedback is provided."""

    def __init__(self, huddle):
        super().__init__(
            name="wait",
            description="Waits until any child completes or feedback is provided"
        )
        self.huddle = huddle

    async def execute(self, **kwargs) -> ToolResult:
        """Wait for completion or feedback."""
        try:
            print(f"[{self.huddle.huddle_id}] Waiting for completion or feedback...")

            # Use huddle's wait method
            await self.huddle.wait()

            return ToolResult(
                success=True,
                message=f"Woke up from wait"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to wait: {e}"
            )
