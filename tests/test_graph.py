"""Tests for graph components."""

import pytest
from dynamic_bot_org_chart.core.graph import Graph, GraphNode, GraphEdge
from dynamic_bot_org_chart.core.states import ExecutionStatus, HuddleContext, HuddleState
from dynamic_bot_org_chart.core.events import EventBus


class DummyExecutor:
    """Dummy executor for testing."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.context = HuddleContext(
            huddle_id=node_id,
            huddle_type="test",
            state=HuddleState.WAITING
        )

    async def execute(self):
        return {"result": "executed"}


def test_graph_node_creation():
    """Test GraphNode creation."""
    executor = DummyExecutor("test-node")
    node = GraphNode(
        node_id="test-node",
        executor=executor,
        context=executor.context
    )

    assert node.node_id == "test-node"
    assert node.execution_status == ExecutionStatus.PENDING
    assert len(node.dependencies) == 0


def test_graph_node_dependencies():
    """Test GraphNode dependencies."""
    executor = DummyExecutor("test-node")
    node = GraphNode(
        node_id="test-node",
        executor=executor,
        context=executor.context
    )

    # Add dependencies
    node.add_dependency("dep-1")
    node.add_dependency("dep-2")

    assert len(node.dependencies) == 2
    assert "dep-1" in node.dependencies

    # Not ready to execute (dependencies not completed)
    assert not node.is_ready_to_execute()

    # Mark dependencies as completed
    node.mark_dependency_completed("dep-1")
    node.mark_dependency_completed("dep-2")

    # Now ready to execute
    assert node.is_ready_to_execute()


def test_graph_edge():
    """Test GraphEdge."""
    edge = GraphEdge(source_id="source", target_id="target")

    assert edge.source_id == "source"
    assert edge.target_id == "target"
    assert edge.should_trigger(None)  # No condition, always trigger


def test_graph_creation():
    """Test Graph creation."""
    event_bus = EventBus()
    graph = Graph(event_bus)

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_graph_add_nodes():
    """Test adding nodes to graph."""
    event_bus = EventBus()
    graph = Graph(event_bus)

    # Create nodes
    executor1 = DummyExecutor("node-1")
    node1 = GraphNode(
        node_id="node-1",
        executor=executor1,
        context=executor1.context
    )

    executor2 = DummyExecutor("node-2")
    node2 = GraphNode(
        node_id="node-2",
        executor=executor2,
        context=executor2.context
    )

    # Add nodes
    graph.add_node(node1)
    graph.add_node(node2)

    assert len(graph.nodes) == 2
    assert "node-1" in graph.nodes
    assert "node-2" in graph.nodes


def test_graph_add_edges():
    """Test adding edges to graph."""
    event_bus = EventBus()
    graph = Graph(event_bus)

    # Create nodes
    executor1 = DummyExecutor("node-1")
    node1 = GraphNode(
        node_id="node-1",
        executor=executor1,
        context=executor1.context
    )

    executor2 = DummyExecutor("node-2")
    node2 = GraphNode(
        node_id="node-2",
        executor=executor2,
        context=executor2.context
    )

    graph.add_node(node1)
    graph.add_node(node2)

    # Add edge
    edge = GraphEdge(source_id="node-1", target_id="node-2")
    graph.add_edge(edge)

    assert len(graph.edges) == 1
    assert "node-1" in graph.nodes["node-2"].dependencies


def test_graph_entry_nodes():
    """Test getting entry nodes."""
    event_bus = EventBus()
    graph = Graph(event_bus)

    # Create nodes
    executor1 = DummyExecutor("node-1")
    node1 = GraphNode(
        node_id="node-1",
        executor=executor1,
        context=executor1.context
    )

    executor2 = DummyExecutor("node-2")
    node2 = GraphNode(
        node_id="node-2",
        executor=executor2,
        context=executor2.context
    )

    graph.add_node(node1)
    graph.add_node(node2)

    # node-1 -> node-2
    edge = GraphEdge(source_id="node-1", target_id="node-2")
    graph.add_edge(edge)

    # node-1 is entry node (no dependencies)
    entry_nodes = graph.get_entry_nodes()
    assert len(entry_nodes) == 1
    assert entry_nodes[0].node_id == "node-1"


def test_graph_execution_limits():
    """Test execution limit configuration."""
    event_bus = EventBus()
    graph = Graph(event_bus)

    graph.set_execution_timeout(3600)
    graph.set_node_timeout(300)
    graph.set_max_node_executions(10)

    assert graph._execution_timeout == 3600
    assert graph._node_timeout == 300
    assert graph._max_node_executions == 10
