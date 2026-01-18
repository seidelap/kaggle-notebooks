"""Tools available to CEO Product Huddle."""

from typing import Any, Dict, Optional
import asyncio

from dynamic_bot_org_chart.tools.base import Tool, ToolResult


class RequestHumanFeedbackTool(Tool):
    """Tool for CEO to request human feedback."""

    def __init__(self, product_huddle):
        super().__init__(
            name="requestHumanFeedback",
            description="Requests feedback from a human"
        )
        self.product_huddle = product_huddle

    async def execute(self, request: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> ToolResult:
        """Request human feedback."""
        try:
            print("\n" + "=" * 60)
            print("HUMAN FEEDBACK REQUEST")
            print("=" * 60)
            print(f"Request: {request}")
            if context:
                print(f"Context: {context}")
            print("=" * 60)

            # In a real implementation, this would pause and wait for human input
            # For now, we'll simulate with a prompt

            print("\nWaiting for human feedback...")
            print("(In production, system would pause here until human responds)")

            # Simulate human response
            # In production, use actual input mechanism
            human_response = await self._get_human_input()

            print(f"\nHuman Response: {human_response}")
            print("=" * 60)

            return ToolResult(
                success=True,
                data={
                    "request": request,
                    "response": human_response,
                    "context": context
                },
                message=f"Received human feedback: {human_response}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to get human feedback: {e}"
            )

    async def _get_human_input(self) -> str:
        """Get input from human."""
        # In production, this would:
        # 1. Pause the system
        # 2. Send notification to human
        # 3. Wait for human response
        # 4. Resume with response

        # For demo, return simulated response
        await asyncio.sleep(0.5)
        return "Proceed with the plan. Looks good!"
