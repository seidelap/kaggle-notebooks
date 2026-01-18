"""Tests for state management."""

import pytest
from datetime import datetime
from dynamic_bot_org_chart.core.states import (
    ExecutionStatus,
    HuddleState,
    TaskState,
    NodeResult,
    ExecutionMetadata,
    HuddleContext,
    TaskContext,
    map_execution_status_to_huddle_state,
    map_huddle_state_to_execution_status,
)


def test_execution_status_enum():
    """Test ExecutionStatus enum."""
    assert ExecutionStatus.PENDING.value == "pending"
    assert ExecutionStatus.EXECUTING.value == "executing"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"


def test_huddle_state_enum():
    """Test HuddleState enum."""
    assert HuddleState.WAITING.value == "waiting"
    assert HuddleState.BLOCKED.value == "blocked"
    assert HuddleState.EXECUTING.value == "executing"
    assert HuddleState.COMPLETED.value == "completed"
    assert HuddleState.FAILED.value == "failed"


def test_execution_metadata():
    """Test ExecutionMetadata."""
    metadata = ExecutionMetadata()
    assert metadata.execution_count == 0
    assert metadata.execution_time is None
    assert not metadata.is_timed_out
    assert not metadata.is_max_executions_reached

    # Set times
    metadata.start_time = datetime.now()
    metadata.end_time = datetime.now()
    assert metadata.execution_time is not None


def test_huddle_context():
    """Test HuddleContext."""
    context = HuddleContext(
        huddle_id="test-huddle",
        huddle_type="product",
        state=HuddleState.WAITING
    )

    assert context.huddle_id == "test-huddle"
    assert context.state == HuddleState.WAITING

    # Test state transition
    old_state, new_state = context.transition_to(HuddleState.EXECUTING)
    assert old_state == HuddleState.WAITING
    assert new_state == HuddleState.EXECUTING
    assert context.state == HuddleState.EXECUTING

    # Test feedback
    context.add_feedback("source-1", "Test feedback")
    assert len(context.feedback) == 1
    assert context.feedback[0]["source"] == "source-1"


def test_task_context():
    """Test TaskContext."""
    context = TaskContext(
        task_id="test-task",
        project_id="test-project",
        description="Test task",
        state=TaskState.PENDING
    )

    assert context.task_id == "test-task"
    assert context.state == TaskState.PENDING

    # Test state transition
    old_state, new_state = context.transition_to(TaskState.EXECUTING)
    assert old_state == TaskState.PENDING
    assert new_state == TaskState.EXECUTING


def test_state_mapping():
    """Test state mapping functions."""
    # ExecutionStatus to HuddleState
    assert map_execution_status_to_huddle_state(
        ExecutionStatus.PENDING, is_blocked=False
    ) == HuddleState.WAITING

    assert map_execution_status_to_huddle_state(
        ExecutionStatus.PENDING, is_blocked=True
    ) == HuddleState.BLOCKED

    assert map_execution_status_to_huddle_state(
        ExecutionStatus.EXECUTING
    ) == HuddleState.EXECUTING

    # HuddleState to ExecutionStatus
    assert map_huddle_state_to_execution_status(
        HuddleState.WAITING
    ) == ExecutionStatus.PENDING

    assert map_huddle_state_to_execution_status(
        HuddleState.EXECUTING
    ) == ExecutionStatus.EXECUTING

    assert map_huddle_state_to_execution_status(
        HuddleState.COMPLETED
    ) == ExecutionStatus.COMPLETED
