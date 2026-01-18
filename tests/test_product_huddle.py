"""Unit tests for Product Huddle."""

import pytest
import asyncio
from dynamic_bot_org_chart.huddles.product_huddle import ProductHuddle
from dynamic_bot_org_chart.models import OrgChartState, HuddleState


@pytest.fixture
def shared_state():
    """Create a shared state for testing."""
    return OrgChartState()


def test_product_huddle_creation(shared_state):
    """Test Product Huddle creation."""
    huddle = ProductHuddle(
        huddle_id="test-product-1",
        shared_state=shared_state,
        parent_huddle_id=None,
        is_ceo=False
    )

    assert huddle.huddle_id == "test-product-1"
    assert huddle.parent_huddle_id is None
    assert not huddle.is_ceo
    assert huddle.product_owner is not None
    assert huddle.ceo_agent is not None
    assert huddle.swarm is not None


def test_ceo_product_huddle_creation(shared_state):
    """Test CEO Product Huddle creation."""
    huddle = ProductHuddle(
        huddle_id="ceo-product",
        shared_state=shared_state,
        parent_huddle_id=None,
        is_ceo=True
    )

    assert huddle.huddle_id == "ceo-product"
    assert huddle.is_ceo
    assert huddle.product_owner is not None
    assert huddle.ceo_agent is None  # CEO huddle doesn't have separate CEO agent


def test_product_huddle_initial_state(shared_state):
    """Test Product Huddle initial state."""
    huddle = ProductHuddle(
        huddle_id="test-product-2",
        shared_state=shared_state,
        parent_huddle_id="parent-product",
        is_ceo=False
    )

    # Check initial state in shared state
    assert huddle.huddle_id in shared_state.huddle_states
    assert shared_state.huddle_states[huddle.huddle_id] == HuddleState.WAITING


@pytest.mark.asyncio
async def test_product_owner_has_correct_tools(shared_state):
    """Test Product Owner agent has correct tools."""
    huddle = ProductHuddle(
        huddle_id="test-product-3",
        shared_state=shared_state,
        parent_huddle_id="parent-product",
        is_ceo=False
    )

    # Check Product Owner has expected tools
    po_tools = [tool["name"] for tool in huddle.product_owner.tools]

    assert "createProject" in po_tools
    assert "cancelProject" in po_tools
    assert "evaluateCompletedProject" in po_tools
    assert "resolveBlocker" in po_tools
    assert "wait" in po_tools
    assert "provideFeedback" in po_tools
    assert "escalate" in po_tools  # Non-CEO should have escalate


@pytest.mark.asyncio
async def test_ceo_has_human_feedback_tool(shared_state):
    """Test CEO has request human feedback tool."""
    huddle = ProductHuddle(
        huddle_id="ceo-product",
        shared_state=shared_state,
        parent_huddle_id=None,
        is_ceo=True
    )

    # Check CEO has requestHumanFeedback tool
    ceo_tools = [tool["name"] for tool in huddle.product_owner.tools]

    assert "requestHumanFeedback" in ceo_tools
    assert "escalate" not in ceo_tools  # CEO should not have escalate


@pytest.mark.asyncio
async def test_tool_executor_with_context(shared_state):
    """Test tool executor provides correct context."""
    huddle = ProductHuddle(
        huddle_id="test-product-4",
        shared_state=shared_state,
        parent_huddle_id="parent-product",
        is_ceo=False
    )

    # Create a tool executor
    executor = huddle._create_tool_executor()

    # Test wait tool execution
    result = await executor("wait", {"timeout": 10})

    assert result["success"] is True
    assert "test-product-4" in result["message"]
    assert shared_state.huddle_states["test-product-4"] == HuddleState.WAITING
