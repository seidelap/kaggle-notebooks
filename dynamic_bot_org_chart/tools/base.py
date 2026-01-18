"""Base tool implementation."""

from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


class Tool:
    """Base class for all tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    def __str__(self):
        return f"Tool({self.name})"
