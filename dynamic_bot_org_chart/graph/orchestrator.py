"""Graph orchestration using Strands GraphBuilder."""

from typing import Dict, Optional
import logging
from strands.multiagent import GraphBuilder

from dynamic_bot_org_chart.models import OrgChartState, HuddleState, ProjectInfo
from dynamic_bot_org_chart.huddles.product_huddle import ProductHuddle
from dynamic_bot_org_chart.huddles.project_huddle import ProjectHuddle


# Enable debug logging for Strands
logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)


class GraphOrchestrator:
    """Orchestrates the dynamic org chart using Strands Graph."""

    def __init__(self, shared_state: Optional[OrgChartState] = None):
        self.shared_state = shared_state or OrgChartState()
        self.graph_builder = GraphBuilder()
        self.huddles: Dict[str, ProductHuddle | ProjectHuddle] = {}

        # Track graph structure
        self.nodes_created = set()

    def create_ceo_product_huddle(self, huddle_id: str = "ceo-product") -> ProductHuddle:
        """Create the CEO Product Huddle (root node)."""
        print(f"Creating CEO Product Huddle: {huddle_id}")

        huddle = ProductHuddle(
            huddle_id=huddle_id,
            shared_state=self.shared_state,
            parent_huddle_id=None,
            is_ceo=True
        )

        # Add to graph as root node
        self.graph_builder.add_node(huddle.swarm, huddle_id)
        self.huddles[huddle_id] = huddle
        self.nodes_created.add(huddle_id)

        print(f"✓ CEO Product Huddle created: {huddle_id}")
        return huddle

    def create_project_from_pending(self):
        """Create project nodes from pending graph nodes in shared state."""
        # Check if there are pending project nodes to create
        if not self.shared_state.pending_graph_nodes:
            return

        for node_info in self.shared_state.pending_graph_nodes:
            if node_info["type"] == "project":
                project_id = node_info["id"]
                parent_id = node_info["parent"]
                project_info = node_info["project_info"]

                # Skip if already created
                if project_id in self.nodes_created:
                    continue

                print(f"Creating Project Huddle: {project_id}")

                # Create Project Huddle
                project_huddle = ProjectHuddle(
                    project_info=project_info,
                    shared_state=self.shared_state
                )

                # Add to graph
                self.graph_builder.add_node(project_huddle.swarm, project_id)
                self.huddles[project_id] = project_huddle
                self.nodes_created.add(project_id)

                # Add edge: project (upstream) -> product (downstream)
                # In Strands, edges define dependencies: source depends on target
                # We want: product depends on project completion
                # So: add_edge(project, product)
                self.graph_builder.add_edge(project_id, parent_id)

                print(f"✓ Project Huddle created: {project_id}")
                print(f"✓ Edge created: {project_id} → {parent_id}")

        # Clear pending nodes
        self.shared_state.pending_graph_nodes = []

    async def execute(self, initial_prompt: str = "Manage the organization"):
        """Execute the graph."""
        print("\n" + "=" * 60)
        print("STARTING GRAPH EXECUTION")
        print("=" * 60)

        # Build the graph (compile it)
        graph = self.graph_builder.compile()

        # Stream events from graph execution
        async for event in graph.stream_async(initial_prompt):
            # Handle different event types
            if event.get("type") == "multiagent_node_start":
                node_id = event['node_id']
                print(f"\n{'=' * 60}")
                print(f"NODE EXECUTION START: {node_id}")
                print(f"{'=' * 60}")

                # Check for pending projects and create them
                self.create_project_from_pending()

            elif event.get("type") == "multiagent_node_stream":
                # Stream inner events
                inner_event = event["event"]
                if "data" in inner_event:
                    print(inner_event["data"], end="")

            elif event.get("type") == "multiagent_node_end":
                node_id = event['node_id']
                print(f"\n{'=' * 60}")
                print(f"NODE EXECUTION END: {node_id}")
                print(f"{'=' * 60}")

                # Check for pending projects after node execution
                self.create_project_from_pending()

                # If new projects were created, rebuild and continue
                if self.shared_state.pending_graph_nodes:
                    print("\n⚠ New projects created, rebuilding graph...")
                    self.create_project_from_pending()

            elif event.get("type") == "multiagent_result":
                result = event["result"]
                print(f"\n\n{'=' * 60}")
                print("GRAPH EXECUTION COMPLETED")
                print(f"{'=' * 60}")
                print(f"Result: {result}")
                return result

        print("\n\n{'=' * 60}")
        print("GRAPH EXECUTION FINISHED")
        print(f"{'=' * 60}")
        return None

    def visualize(self) -> str:
        """Visualize the graph structure."""
        lines = ["Graph Structure:"]
        lines.append("=" * 60)

        for node_id in self.nodes_created:
            huddle = self.huddles.get(node_id)
            if huddle:
                state = self.shared_state.huddle_states.get(node_id, HuddleState.WAITING)
                huddle_type = "CEO Product" if getattr(huddle, 'is_ceo', False) else \
                              "Product" if isinstance(huddle, ProductHuddle) else "Project"

                lines.append(f"\n{node_id} ({huddle_type})")
                lines.append(f"  State: {state.value}")

                # Show parent for non-CEO
                if huddle.parent_huddle_id:
                    lines.append(f"  Parent: {huddle.parent_huddle_id}")

                # Show projects for Product Huddles
                if isinstance(huddle, ProductHuddle):
                    projects = [
                        pid for pid, p in self.shared_state.projects.items()
                        if p.parent_product_id == node_id
                    ]
                    if projects:
                        lines.append(f"  Projects: {', '.join(projects)}")

                # Show tasks for Project Huddles
                if isinstance(huddle, ProjectHuddle):
                    tasks = [
                        tid for tid, t in self.shared_state.tasks.items()
                        if t.project_id == node_id
                    ]
                    if tasks:
                        lines.append(f"  Tasks: {', '.join(tasks)}")

        return "\n".join(lines)

    def get_state_summary(self) -> Dict:
        """Get summary of the current state."""
        return {
            "nodes_created": len(self.nodes_created),
            "projects": len(self.shared_state.projects),
            "tasks": len(self.shared_state.tasks),
            "escalations": len(self.shared_state.escalations),
            "feedback": len(self.shared_state.feedback),
            "huddle_states": {
                node_id: state.value
                for node_id, state in self.shared_state.huddle_states.items()
            }
        }
