"""State models for the Dynamic Bot Org Chart."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class HuddleState(str, Enum):
    """State of a huddle."""
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskState(str, Enum):
    """State of a task (Claude Code session)."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProjectInfo(BaseModel):
    """Project information."""
    id: str
    parent_product_id: str
    description: str
    artifact_specification: str
    execution_timeout: Optional[int] = None
    state: HuddleState = HuddleState.WAITING
    artifact: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TaskInfo(BaseModel):
    """Task (Claude Code session) information."""
    id: str
    project_id: str
    description: str
    test_requirements: str
    execution_timeout: Optional[int] = None
    codebase_context: Dict[str, Any] = Field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    artifact: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class EscalationInfo(BaseModel):
    """Escalation information."""
    from_huddle: str
    to_huddle: str
    reason: str
    wait: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class FeedbackInfo(BaseModel):
    """Feedback information."""
    from_huddle: str
    to_huddle: str
    feedback: str
    created_at: datetime = Field(default_factory=datetime.now)


class OrgChartState(BaseModel):
    """Shared state for the entire org chart."""
    projects: Dict[str, ProjectInfo] = Field(default_factory=dict)
    tasks: Dict[str, TaskInfo] = Field(default_factory=dict)
    escalations: list[EscalationInfo] = Field(default_factory=list)
    feedback: list[FeedbackInfo] = Field(default_factory=list)
    huddle_states: Dict[str, HuddleState] = Field(default_factory=dict)
    human_feedback_requests: list[Dict[str, Any]] = Field(default_factory=list)

    # Graph structure
    pending_graph_nodes: list[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        use_enum_values = True
