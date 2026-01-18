"""Dynamic Bot Org Chart - Agent-based framework built on AWS Strands Agents."""

__version__ = "1.0.0"

from dynamic_bot_org_chart.models import (
    OrgChartState,
    HuddleState,
    TaskState,
    ProjectInfo,
    TaskInfo,
    EscalationInfo,
    FeedbackInfo,
)
from dynamic_bot_org_chart.graph.orchestrator import GraphOrchestrator
from dynamic_bot_org_chart.huddles.product_huddle import ProductHuddle
from dynamic_bot_org_chart.huddles.project_huddle import ProjectHuddle

__all__ = [
    "OrgChartState",
    "HuddleState",
    "TaskState",
    "ProjectInfo",
    "TaskInfo",
    "EscalationInfo",
    "FeedbackInfo",
    "GraphOrchestrator",
    "ProductHuddle",
    "ProjectHuddle",
]
