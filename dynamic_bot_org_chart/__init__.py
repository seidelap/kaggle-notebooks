"""Dynamic Bot Org Chart - Agent-based framework for managing products and projects."""

__version__ = "0.1.0"

from dynamic_bot_org_chart.core.states import (
    ExecutionStatus,
    HuddleState,
    TaskState,
    NodeResult,
)
from dynamic_bot_org_chart.core.graph import Graph, GraphNode, GraphEdge

__all__ = [
    "ExecutionStatus",
    "HuddleState",
    "TaskState",
    "NodeResult",
    "Graph",
    "GraphNode",
    "GraphEdge",
]
