"""State management for the Dynamic Bot Org Chart framework."""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class ExecutionStatus(Enum):
    """Graph node execution status."""

    PENDING = "pending"  # Maps to WAITING or BLOCKED
    EXECUTING = "executing"  # Active execution
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed execution


class HuddleState(Enum):
    """Huddle (Product/Project) state."""

    WAITING = "waiting"  # Non-escalatory, waiting for dependencies
    BLOCKED = "blocked"  # Escalatory, waiting for parent resolution
    EXECUTING = "executing"  # Active execution
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed execution


class TaskState(Enum):
    """Task (Claude Code session) state."""

    PENDING = "pending"  # Created but not started
    EXECUTING = "executing"  # Claude Code session running
    BLOCKED = "blocked"  # Claude Code returned blocked status
    COMPLETED = "completed"  # Completed successfully
    FAILED = "failed"  # Failed or timed out


class NodeResult(Enum):
    """Result after node execution."""

    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ExecutionMetadata:
    """Metadata for execution tracking."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_count: int = 0
    timeout: Optional[int] = None  # seconds
    max_executions: Optional[int] = None

    @property
    def execution_time(self) -> Optional[float]:
        """Calculate execution time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_timed_out(self) -> bool:
        """Check if execution has timed out."""
        if self.timeout and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return elapsed > self.timeout
        return False

    @property
    def is_max_executions_reached(self) -> bool:
        """Check if max executions reached."""
        if self.max_executions:
            return self.execution_count >= self.max_executions
        return False


@dataclass
class HuddleContext:
    """Context for a huddle execution."""

    huddle_id: str
    huddle_type: str  # "product" or "project"
    state: HuddleState
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)
    artifact: Optional[Any] = None
    error: Optional[str] = None
    escalation_reason: Optional[str] = None
    feedback: list[dict] = field(default_factory=list)

    def transition_to(self, new_state: HuddleState, reason: Optional[str] = None):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state

        # Update metadata
        if new_state == HuddleState.EXECUTING:
            if self.metadata.start_time is None:
                self.metadata.start_time = datetime.now()
            self.metadata.execution_count += 1
        elif new_state in (HuddleState.COMPLETED, HuddleState.FAILED):
            self.metadata.end_time = datetime.now()
        elif new_state == HuddleState.BLOCKED:
            self.escalation_reason = reason

        return old_state, new_state

    def add_feedback(self, source: str, feedback: str):
        """Add feedback to the context."""
        self.feedback.append({
            "source": source,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        })


@dataclass
class TaskContext:
    """Context for a task (Claude Code session) execution."""

    task_id: str
    project_id: str
    description: str
    state: TaskState
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)
    artifact: Optional[Any] = None
    test_results: Optional[dict] = None
    error: Optional[str] = None

    def transition_to(self, new_state: TaskState):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state

        # Update metadata
        if new_state == TaskState.EXECUTING:
            if self.metadata.start_time is None:
                self.metadata.start_time = datetime.now()
            self.metadata.execution_count += 1
        elif new_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.BLOCKED):
            self.metadata.end_time = datetime.now()

        return old_state, new_state


def map_execution_status_to_huddle_state(
    status: ExecutionStatus,
    is_blocked: bool = False
) -> HuddleState:
    """Map GraphNode execution status to huddle state."""
    if status == ExecutionStatus.PENDING:
        return HuddleState.BLOCKED if is_blocked else HuddleState.WAITING
    elif status == ExecutionStatus.EXECUTING:
        return HuddleState.EXECUTING
    elif status == ExecutionStatus.COMPLETED:
        return HuddleState.COMPLETED
    elif status == ExecutionStatus.FAILED:
        return HuddleState.FAILED
    return HuddleState.WAITING


def map_huddle_state_to_execution_status(state: HuddleState) -> ExecutionStatus:
    """Map huddle state to GraphNode execution status."""
    if state in (HuddleState.WAITING, HuddleState.BLOCKED):
        return ExecutionStatus.PENDING
    elif state == HuddleState.EXECUTING:
        return ExecutionStatus.EXECUTING
    elif state == HuddleState.COMPLETED:
        return ExecutionStatus.COMPLETED
    elif state == HuddleState.FAILED:
        return ExecutionStatus.FAILED
    return ExecutionStatus.PENDING
