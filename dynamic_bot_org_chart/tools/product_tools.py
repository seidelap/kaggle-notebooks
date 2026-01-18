"""Tools available to Product Huddles."""

from typing import Any, Dict, Optional
import uuid

from dynamic_bot_org_chart.tools.base import Tool, ToolResult
from dynamic_bot_org_chart.core.graph import Graph
from dynamic_bot_org_chart.core.states import HuddleState


class CreateProjectTool(Tool):
    """Tool for creating a new project."""

    def __init__(self, graph: Graph, product_huddle):
        super().__init__(
            name="createProject",
            description="Creates a new Project Huddle with artifact specification"
        )
        self.graph = graph
        self.product_huddle = product_huddle

    async def execute(
        self,
        description: str,
        artifact_specification: str,
        execution_timeout: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        """Create a new project."""
        try:
            # Import here to avoid circular import
            from dynamic_bot_org_chart.huddles.project_huddle import ProjectHuddle

            # Generate project ID
            project_id = f"project-{uuid.uuid4().hex[:8]}"

            print(f"[{self.product_huddle.huddle_id}] Creating project: {project_id}")

            # Create project huddle
            project_huddle = ProjectHuddle(
                huddle_id=project_id,
                event_bus=self.graph.event_bus,
                parent_huddle_id=self.product_huddle.huddle_id,
                description=description,
                artifact_specification=artifact_specification,
                execution_timeout=execution_timeout
            )

            # Add to product's children
            self.product_huddle.children[project_id] = project_huddle

            # Add to graph
            from dynamic_bot_org_chart.core.graph import GraphNode, GraphEdge
            from dynamic_bot_org_chart.core.states import ExecutionStatus

            node = GraphNode(
                node_id=project_id,
                executor=project_huddle,
                context=project_huddle.context
            )
            self.graph.add_node(node)

            # Create edge: project (upstream) -> product (downstream)
            edge = GraphEdge(
                source_id=project_id,
                target_id=self.product_huddle.huddle_id
            )
            self.graph.add_edge(edge)

            return ToolResult(
                success=True,
                data={
                    "project_id": project_id,
                    "description": description,
                    "artifact_specification": artifact_specification
                },
                message=f"Project {project_id} created successfully"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to create project: {e}"
            )


class CancelProjectTool(Tool):
    """Tool for cancelling a project."""

    def __init__(self, graph: Graph, product_huddle):
        super().__init__(
            name="cancelProject",
            description="Cancels a project"
        )
        self.graph = graph
        self.product_huddle = product_huddle

    async def execute(self, project_id: str, **kwargs) -> ToolResult:
        """Cancel a project."""
        try:
            project = self.product_huddle.children.get(project_id)
            if not project:
                return ToolResult(
                    success=False,
                    error="Project not found",
                    message=f"Project {project_id} not found"
                )

            print(f"[{self.product_huddle.huddle_id}] Cancelling project: {project_id}")

            # Transition to FAILED state
            project.context.transition_to(HuddleState.FAILED)
            project.context.error = "Cancelled by product owner"

            # Mark as failed in graph
            await self.graph.mark_node_failed(project_id, "Cancelled by product owner")

            return ToolResult(
                success=True,
                data={"project_id": project_id},
                message=f"Project {project_id} cancelled successfully"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to cancel project: {e}"
            )


class EvaluateCompletedProjectTool(Tool):
    """Tool for evaluating a completed project."""

    def __init__(self, graph: Graph, product_huddle):
        super().__init__(
            name="evaluateCompletedProject",
            description="Evaluates a completed project and decides next action"
        )
        self.graph = graph
        self.product_huddle = product_huddle

    async def execute(self, project_id: str, convert_to_product: bool = False, **kwargs) -> ToolResult:
        """Evaluate a completed project."""
        try:
            project = self.product_huddle.children.get(project_id)
            if not project:
                return ToolResult(
                    success=False,
                    error="Project not found",
                    message=f"Project {project_id} not found"
                )

            if project.context.state != HuddleState.COMPLETED:
                return ToolResult(
                    success=False,
                    error="Project not completed",
                    message=f"Project {project_id} is not completed yet"
                )

            print(f"[{self.product_huddle.huddle_id}] Evaluating project: {project_id}")

            if convert_to_product:
                # Convert to new product
                print(f"[{self.product_huddle.huddle_id}] Converting {project_id} to new product")

                # In a real implementation, create a new ProductHuddle
                # For now, just mark as evaluated
                action = "converted_to_product"
            else:
                # Keep as part of parent product
                print(f"[{self.product_huddle.huddle_id}] Keeping {project_id} as part of product")
                action = "kept_in_product"

            return ToolResult(
                success=True,
                data={
                    "project_id": project_id,
                    "action": action,
                    "artifact": project.context.artifact
                },
                message=f"Project {project_id} evaluated: {action}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to evaluate project: {e}"
            )
