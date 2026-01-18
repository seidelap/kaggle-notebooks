"""Integration tests for Graph orchestration."""

import pytest
from dynamic_bot_org_chart.graph.orchestrator import GraphOrchestrator
from dynamic_bot_org_chart.models import OrgChartState, HuddleState


def test_graph_orchestrator_creation():
    """Test GraphOrchestrator creation."""
    orchestrator = GraphOrchestrator()

    assert orchestrator.shared_state is not None
    assert orchestrator.graph_builder is not None
    assert len(orchestrator.huddles) == 0
    assert len(orchestrator.nodes_created) == 0


def test_create_ceo_product_huddle():
    """Test creating CEO Product Huddle."""
    orchestrator = GraphOrchestrator()

    huddle = orchestrator.create_ceo_product_huddle("ceo-product")

    assert huddle.huddle_id == "ceo-product"
    assert huddle.is_ceo
    assert "ceo-product" in orchestrator.huddles
    assert "ceo-product" in orchestrator.nodes_created
    assert "ceo-product" in orchestrator.shared_state.huddle_states


def test_visualize_empty_graph():
    """Test visualizing an empty graph."""
    orchestrator = GraphOrchestrator()

    visualization = orchestrator.visualize()

    assert "Graph Structure:" in visualization


def test_visualize_with_ceo_huddle():
    """Test visualizing graph with CEO huddle."""
    orchestrator = GraphOrchestrator()
    orchestrator.create_ceo_product_huddle("ceo-product")

    visualization = orchestrator.visualize()

    assert "Graph Structure:" in visualization
    assert "ceo-product" in visualization
    assert "CEO Product" in visualization


def test_get_state_summary():
    """Test getting state summary."""
    orchestrator = GraphOrchestrator()
    orchestrator.create_ceo_product_huddle("ceo-product")

    summary = orchestrator.get_state_summary()

    assert summary["nodes_created"] == 1
    assert summary["projects"] == 0
    assert summary["tasks"] == 0
    assert "ceo-product" in summary["huddle_states"]


def test_create_project_from_pending():
    """Test creating projects from pending nodes."""
    from dynamic_bot_org_chart.models import ProjectInfo

    orchestrator = GraphOrchestrator()
    orchestrator.create_ceo_product_huddle("ceo-product")

    # Add a pending project
    project_info = ProjectInfo(
        id="test-project-1",
        parent_product_id="ceo-product",
        description="Test project",
        artifact_specification="Test artifact"
    )

    orchestrator.shared_state.projects[project_info.id] = project_info
    orchestrator.shared_state.pending_graph_nodes.append({
        "type": "project",
        "id": project_info.id,
        "parent": "ceo-product",
        "project_info": project_info
    })

    # Create projects from pending
    orchestrator.create_project_from_pending()

    # Verify project was created
    assert "test-project-1" in orchestrator.nodes_created
    assert "test-project-1" in orchestrator.huddles
    assert len(orchestrator.shared_state.pending_graph_nodes) == 0


@pytest.mark.asyncio
async def test_graph_execution_basic():
    """Test basic graph execution."""
    orchestrator = GraphOrchestrator()
    orchestrator.create_ceo_product_huddle("ceo-product")

    # Note: This test would require mock/stub for actual Strands execution
    # For now, we test that the orchestrator is set up correctly
    assert orchestrator.graph_builder is not None
    assert len(orchestrator.nodes_created) == 1
