"""Graph structure for managing huddle dependencies."""

from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
import asyncio
from datetime import datetime

from dynamic_bot_org_chart.core.states import (
    ExecutionStatus,
    NodeResult,
    ExecutionMetadata,
)
from dynamic_bot_org_chart.core.events import Event, EventType, EventBus


@dataclass
class GraphEdge:
    """Edge connecting two graph nodes."""

    source_id: str  # upstream node (e.g., project)
    target_id: str  # downstream node (e.g., product)
    condition: Optional[Callable[[Any], bool]] = None  # optional condition for edge

    def should_trigger(self, result: Any) -> bool:
        """Check if this edge should trigger based on result."""
        if self.condition:
            return self.condition(result)
        return True


@dataclass
class GraphNode:
    """Node in the dependency graph."""

    node_id: str
    executor: Any  # The Swarm/Huddle instance
    dependencies: Set[str] = field(default_factory=set)  # upstream nodes
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[NodeResult] = None
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)
    context: Optional[Any] = None  # HuddleContext

    # Runtime state
    _completed_dependencies: Set[str] = field(default_factory=set)
    _blocked: bool = False
    _waiting_for_feedback: bool = False

    def add_dependency(self, node_id: str):
        """Add a dependency on another node."""
        self.dependencies.add(node_id)

    def remove_dependency(self, node_id: str):
        """Remove a dependency on another node."""
        self.dependencies.discard(node_id)

    def mark_dependency_completed(self, node_id: str):
        """Mark a dependency as completed."""
        if node_id in self.dependencies:
            self._completed_dependencies.add(node_id)

    def is_ready_to_execute(self) -> bool:
        """Check if this node is ready to execute."""
        # Must be in PENDING status
        if self.execution_status != ExecutionStatus.PENDING:
            return False

        # Must not be blocked
        if self._blocked:
            return False

        # Must not be waiting for feedback (unless woken up)
        if self._waiting_for_feedback:
            return False

        # All dependencies must be completed
        return self._completed_dependencies >= self.dependencies

    def mark_blocked(self, blocked: bool = True):
        """Mark this node as blocked."""
        self._blocked = blocked

    def mark_waiting_for_feedback(self, waiting: bool = True):
        """Mark this node as waiting for feedback."""
        self._waiting_for_feedback = waiting

    def wake_up(self):
        """Wake up this node (unblock and stop waiting for feedback)."""
        self._blocked = False
        self._waiting_for_feedback = False


class Graph:
    """Dependency graph for managing huddles."""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.event_bus = event_bus or EventBus()

        # Execution settings
        self._execution_timeout: Optional[int] = None  # seconds
        self._node_timeout: Optional[int] = None  # seconds per node
        self._max_node_executions: Optional[int] = None

    def set_execution_timeout(self, timeout: int):
        """Set maximum total execution time for the graph."""
        self._execution_timeout = timeout

    def set_node_timeout(self, timeout: int):
        """Set maximum time per node execution."""
        self._node_timeout = timeout

    def set_max_node_executions(self, max_executions: int):
        """Set maximum node executions (for cyclic graphs)."""
        self._max_node_executions = max_executions

    def add_node(self, node: GraphNode):
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

        # Apply graph-level settings to node metadata
        if self._node_timeout:
            node.metadata.timeout = self._node_timeout
        if self._max_node_executions:
            node.metadata.max_executions = self._max_node_executions

    def remove_node(self, node_id: str):
        """Remove a node from the graph."""
        if node_id in self.nodes:
            # Remove all edges involving this node
            self.edges = [
                e for e in self.edges
                if e.source_id != node_id and e.target_id != node_id
            ]
            # Remove from other nodes' dependencies
            for node in self.nodes.values():
                node.remove_dependency(node_id)
            del self.nodes[node_id]

    def add_edge(self, edge: GraphEdge):
        """Add an edge to the graph."""
        self.edges.append(edge)

        # Add dependency to target node
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].add_dependency(edge.source_id)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_entry_nodes(self) -> List[GraphNode]:
        """Get all entry nodes (no dependencies)."""
        return [node for node in self.nodes.values() if not node.dependencies]

    def get_downstream_nodes(self, node_id: str) -> List[GraphNode]:
        """Get all downstream nodes (nodes that depend on this node)."""
        downstream_ids = {edge.target_id for edge in self.edges if edge.source_id == node_id}
        return [self.nodes[nid] for nid in downstream_ids if nid in self.nodes]

    def get_upstream_nodes(self, node_id: str) -> List[GraphNode]:
        """Get all upstream nodes (dependencies of this node)."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[dep_id] for dep_id in node.dependencies if dep_id in self.nodes]

    async def mark_node_completed(self, node_id: str, result: NodeResult, artifact: Any = None):
        """Mark a node as completed and trigger downstream nodes."""
        node = self.nodes.get(node_id)
        if not node:
            return

        # Update node status
        node.execution_status = ExecutionStatus.COMPLETED
        node.result = result
        if artifact:
            node.context.artifact = artifact

        # Notify downstream nodes
        for edge in self.edges:
            if edge.source_id == node_id:
                downstream_node = self.nodes.get(edge.target_id)
                if downstream_node:
                    downstream_node.mark_dependency_completed(node_id)

                    # Publish dependency completed event
                    await self.event_bus.publish(Event(
                        event_type=EventType.DEPENDENCY_COMPLETED,
                        source_id=node_id,
                        target_id=edge.target_id,
                        data={"result": result, "artifact": artifact}
                    ))

    async def mark_node_failed(self, node_id: str, error: str):
        """Mark a node as failed."""
        node = self.nodes.get(node_id)
        if not node:
            return

        # Update node status
        node.execution_status = ExecutionStatus.FAILED
        node.result = NodeResult.FAILED
        if node.context:
            node.context.error = error

        # Publish dependency failed event
        for edge in self.edges:
            if edge.source_id == node_id:
                await self.event_bus.publish(Event(
                    event_type=EventType.DEPENDENCY_FAILED,
                    source_id=node_id,
                    target_id=edge.target_id,
                    data={"error": error}
                ))

    async def escalate(self, source_id: str, target_id: str, reason: str):
        """Escalate from one node to another."""
        source_node = self.nodes.get(source_id)
        if source_node:
            source_node.mark_blocked(True)
            if source_node.context:
                source_node.context.escalation_reason = reason

        # Publish escalation event (wake-up signal)
        await self.event_bus.publish(Event(
            event_type=EventType.ESCALATION_REQUESTED,
            source_id=source_id,
            target_id=target_id,
            data={"reason": reason}
        ))

    async def resolve_blocker(self, parent_id: str, child_id: str):
        """Resolve a blocker in a child node."""
        child_node = self.nodes.get(child_id)
        if child_node:
            child_node.wake_up()

        # Publish blocker resolved event (wake-up signal)
        await self.event_bus.publish(Event(
            event_type=EventType.BLOCKER_RESOLVED,
            source_id=parent_id,
            target_id=child_id,
            data={}
        ))

    async def provide_feedback(self, source_id: str, target_id: str, feedback: str):
        """Provide feedback from one node to another."""
        target_node = self.nodes.get(target_id)
        if target_node and target_node.context:
            target_node.context.add_feedback(source_id, feedback)
            target_node.wake_up()

        # Publish feedback event
        await self.event_bus.publish(Event(
            event_type=EventType.FEEDBACK_PROVIDED,
            source_id=source_id,
            target_id=target_id,
            data={"feedback": feedback}
        ))

    def topological_sort(self) -> List[str]:
        """Get topological sort of nodes (for visualization)."""
        # Kahn's algorithm
        in_degree = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            # Reduce in-degree for downstream nodes
            for edge in self.edges:
                if edge.source_id == node_id:
                    in_degree[edge.target_id] -= 1
                    if in_degree[edge.target_id] == 0:
                        queue.append(edge.target_id)

        return result

    def visualize(self) -> str:
        """Generate a text visualization of the graph."""
        lines = ["Graph Structure:"]
        lines.append("=" * 50)

        # Sort nodes topologically
        sorted_nodes = self.topological_sort()

        for node_id in sorted_nodes:
            node = self.nodes[node_id]
            status_symbol = {
                ExecutionStatus.PENDING: "⏸",
                ExecutionStatus.EXECUTING: "▶",
                ExecutionStatus.COMPLETED: "✓",
                ExecutionStatus.FAILED: "✗",
            }.get(node.execution_status, "?")

            lines.append(f"\n{status_symbol} {node_id} ({node.execution_status.value})")

            # Show dependencies
            if node.dependencies:
                lines.append(f"  Dependencies: {', '.join(node.dependencies)}")

            # Show downstream nodes
            downstream = self.get_downstream_nodes(node_id)
            if downstream:
                lines.append(f"  Downstream: {', '.join(n.node_id for n in downstream)}")

        return "\n".join(lines)
