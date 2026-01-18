"""Unit tests for Project Huddle."""

import pytest
import asyncio
from dynamic_bot_org_chart.huddles.project_huddle import ProjectHuddle
from dynamic_bot_org_chart.models import OrgChartState, ProjectInfo, HuddleState


@pytest.fixture
def shared_state():
    """Create a shared state for testing."""
    return OrgChartState()


@pytest.fixture
def project_info():
    """Create a project info for testing."""
    return ProjectInfo(
        id="test-project-1",
        parent_product_id="parent-product",
        description="Build a REST API",
        artifact_specification="A working REST API with tests"
    )


def test_project_huddle_creation(shared_state, project_info):
    """Test Project Huddle creation."""
    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    assert huddle.huddle_id == "test-project-1"
    assert huddle.parent_huddle_id == "parent-product"
    assert huddle.project_lead is not None
    assert huddle.product_owner is not None
    assert huddle.ceo_agent is not None
    assert huddle.swarm is not None


def test_project_huddle_initial_state(shared_state, project_info):
    """Test Project Huddle initial state."""
    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    # Check initial state in shared state
    assert huddle.huddle_id in shared_state.huddle_states
    assert shared_state.huddle_states[huddle.huddle_id] == HuddleState.WAITING


@pytest.mark.asyncio
async def test_project_lead_has_correct_tools(shared_state, project_info):
    """Test Project Lead agent has correct tools."""
    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    # Check Project Lead has expected tools
    pl_tools = [tool["name"] for tool in huddle.project_lead.tools]

    assert "createTask" in pl_tools
    assert "cancelTask" in pl_tools
    assert "completeProject" in pl_tools
    assert "escalate" in pl_tools
    assert "resolveBlocker" in pl_tools
    assert "wait" in pl_tools
    assert "provideFeedback" in pl_tools


@pytest.mark.asyncio
async def test_project_lead_system_prompt_includes_specs(shared_state):
    """Test Project Lead system prompt includes project specifications."""
    project_info = ProjectInfo(
        id="test-project-2",
        parent_product_id="parent-product",
        description="Build feature X",
        artifact_specification="Feature X implementation with tests"
    )

    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    # Check system prompt includes project description and artifact specification
    prompt = huddle.project_lead.system_prompt

    assert "Build feature X" in prompt
    assert "Feature X implementation with tests" in prompt


@pytest.mark.asyncio
async def test_tool_executor_with_context(shared_state, project_info):
    """Test tool executor provides correct context."""
    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    # Create a tool executor
    executor = huddle._create_tool_executor()

    # Test wait tool execution
    result = await executor("wait", {"timeout": 10})

    assert result["success"] is True
    assert "test-project-1" in result["message"]
    assert shared_state.huddle_states["test-project-1"] == HuddleState.WAITING


@pytest.mark.asyncio
async def test_create_task_tool_execution(shared_state, project_info):
    """Test createTask tool execution."""
    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    executor = huddle._create_tool_executor()

    # Test createTask execution
    result = await executor("createTask", {
        "description": "Implement endpoint /users",
        "test_requirements": "Test GET /users returns user list"
    })

    assert result["success"] is True
    assert "task_id" in result
    assert result["task_id"] in shared_state.tasks


@pytest.mark.asyncio
async def test_complete_project_tool_execution(shared_state, project_info):
    """Test completeProject tool execution."""
    # Add project to shared state first
    shared_state.projects[project_info.id] = project_info

    huddle = ProjectHuddle(
        project_info=project_info,
        shared_state=shared_state
    )

    executor = huddle._create_tool_executor()

    # Test completeProject execution
    result = await executor("completeProject", {
        "artifact": {"code": "REST API implementation"},
        "summary": "Completed REST API"
    })

    assert result["success"] is True
    assert "evaluation_score" in result
    assert shared_state.projects[project_info.id].state == HuddleState.COMPLETED
