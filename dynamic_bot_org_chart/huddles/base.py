"""Base huddle (Swarm) implementation."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from dynamic_bot_org_chart.core.states import HuddleState, HuddleContext
from dynamic_bot_org_chart.core.events import Event, EventType, EventBus


class MemberRole(Enum):
    """Member role in a huddle."""

    HUDDLE_LEAD = "huddle_lead"
    MEMBER = "member"


@dataclass
class HuddleMember:
    """Member of a huddle."""

    member_id: str
    name: str
    role: MemberRole
    system_prompt: str
    tools: List[str] = field(default_factory=list)

    @property
    def is_lead(self) -> bool:
        """Check if this member is the huddle lead."""
        return self.role == MemberRole.HUDDLE_LEAD


class BaseHuddle:
    """Base class for all huddles (Swarms)."""

    def __init__(
        self,
        huddle_id: str,
        huddle_type: str,
        members: List[HuddleMember],
        event_bus: EventBus,
        parent_huddle_id: Optional[str] = None
    ):
        self.huddle_id = huddle_id
        self.huddle_type = huddle_type
        self.members = members
        self.event_bus = event_bus
        self.parent_huddle_id = parent_huddle_id

        # Context
        self.context = HuddleContext(
            huddle_id=huddle_id,
            huddle_type=huddle_type,
            state=HuddleState.WAITING
        )

        # Children tracking (for products/projects)
        self.children: Dict[str, Any] = {}

        # Tools available to this huddle
        self.tools: Dict[str, Callable] = {}

        # Subscribe to relevant events
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        # Subscribe to events targeted at this huddle
        self.event_bus.subscribe(
            EventType.ESCALATION_REQUESTED,
            self._handle_escalation,
            target_id=self.huddle_id
        )
        self.event_bus.subscribe(
            EventType.BLOCKER_RESOLVED,
            self._handle_blocker_resolved,
            target_id=self.huddle_id
        )
        self.event_bus.subscribe(
            EventType.FEEDBACK_PROVIDED,
            self._handle_feedback,
            target_id=self.huddle_id
        )
        self.event_bus.subscribe(
            EventType.DEPENDENCY_COMPLETED,
            self._handle_dependency_completed,
            target_id=self.huddle_id
        )

    async def _handle_escalation(self, event: Event):
        """Handle escalation event."""
        reason = event.data.get("reason", "")
        print(f"[{self.huddle_id}] Received escalation from {event.source_id}: {reason}")
        # Wake up if waiting
        if self.context.state == HuddleState.WAITING:
            self.context.transition_to(HuddleState.EXECUTING)

    async def _handle_blocker_resolved(self, event: Event):
        """Handle blocker resolved event."""
        print(f"[{self.huddle_id}] Blocker resolved by {event.source_id}")
        # Wake up if blocked
        if self.context.state == HuddleState.BLOCKED:
            self.context.transition_to(HuddleState.WAITING)

    async def _handle_feedback(self, event: Event):
        """Handle feedback event."""
        feedback = event.data.get("feedback", "")
        print(f"[{self.huddle_id}] Received feedback from {event.source_id}: {feedback}")
        self.context.add_feedback(event.source_id, feedback)
        # Wake up if waiting
        if self.context.state == HuddleState.WAITING:
            self.context.transition_to(HuddleState.EXECUTING)

    async def _handle_dependency_completed(self, event: Event):
        """Handle dependency completed event."""
        print(f"[{self.huddle_id}] Dependency {event.source_id} completed")
        # Wake up if waiting
        if self.context.state == HuddleState.WAITING:
            self.context.transition_to(HuddleState.EXECUTING)

    def get_huddle_lead(self) -> Optional[HuddleMember]:
        """Get the huddle lead."""
        for member in self.members:
            if member.is_lead:
                return member
        return None

    def register_tool(self, tool_name: str, tool_func: Callable):
        """Register a tool for this huddle."""
        self.tools[tool_name] = tool_func

    async def execute(self) -> Any:
        """Execute the huddle. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    async def wait(self):
        """Wait until any child completes or feedback is provided."""
        print(f"[{self.huddle_id}] Waiting for completion or feedback...")
        self.context.transition_to(HuddleState.WAITING)

        # Wait for state to change from WAITING
        while self.context.state == HuddleState.WAITING:
            await asyncio.sleep(0.1)

        print(f"[{self.huddle_id}] Woke up with state: {self.context.state.value}")

    async def escalate(self, reason: str, wait: bool = True):
        """Escalate to parent huddle."""
        if not self.parent_huddle_id:
            raise ValueError(f"Huddle {self.huddle_id} has no parent to escalate to")

        print(f"[{self.huddle_id}] Escalating to {self.parent_huddle_id}: {reason}")

        # Transition to BLOCKED state
        self.context.transition_to(HuddleState.BLOCKED, reason=reason)

        # Publish escalation event
        await self.event_bus.publish(Event(
            event_type=EventType.ESCALATION_REQUESTED,
            source_id=self.huddle_id,
            target_id=self.parent_huddle_id,
            data={"reason": reason}
        ))

        # Wait for resolution if requested
        if wait:
            print(f"[{self.huddle_id}] Waiting for blocker resolution...")
            while self.context.state == HuddleState.BLOCKED:
                await asyncio.sleep(0.1)
            print(f"[{self.huddle_id}] Blocker resolved, continuing...")

    async def resolve_blocker(self, child_node_id: str, wait: bool = True):
        """Resolve blocker in a child node."""
        print(f"[{self.huddle_id}] Resolving blocker in {child_node_id}")

        # Publish blocker resolved event
        await self.event_bus.publish(Event(
            event_type=EventType.BLOCKER_RESOLVED,
            source_id=self.huddle_id,
            target_id=child_node_id,
            data={}
        ))

        # Wait if requested
        if wait:
            await asyncio.sleep(0.1)  # Small delay for resolution to propagate

    async def provide_feedback(self, target_huddle: str, feedback: str):
        """Provide feedback to another huddle."""
        print(f"[{self.huddle_id}] Providing feedback to {target_huddle}: {feedback}")

        # Publish feedback event
        await self.event_bus.publish(Event(
            event_type=EventType.FEEDBACK_PROVIDED,
            source_id=self.huddle_id,
            target_id=target_huddle,
            data={"feedback": feedback}
        ))

    def get_context_for_llm(self) -> Dict[str, Any]:
        """Get context to pass to LLM."""
        return {
            "huddle_id": self.huddle_id,
            "huddle_type": self.huddle_type,
            "state": self.context.state.value,
            "feedback": self.context.feedback,
            "children": {
                child_id: child.context.state.value
                for child_id, child in self.children.items()
            },
            "available_tools": list(self.tools.keys())
        }
