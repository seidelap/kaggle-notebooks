"""Event system for the Dynamic Bot Org Chart framework."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


class EventType(Enum):
    """Types of events in the system."""

    # Dependency events
    DEPENDENCY_COMPLETED = "dependency_completed"
    DEPENDENCY_FAILED = "dependency_failed"

    # Escalation events
    ESCALATION_REQUESTED = "escalation_requested"
    BLOCKER_RESOLVED = "blocker_resolved"

    # Feedback events
    FEEDBACK_PROVIDED = "feedback_provided"

    # Task events
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"

    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_FAILED = "project_failed"
    PROJECT_BLOCKED = "project_blocked"

    # State change events
    STATE_CHANGED = "state_changed"

    # Wake-up events
    WAKE_UP = "wake_up"


@dataclass
class Event:
    """Event in the system."""

    event_type: EventType
    source_id: str  # ID of the entity that generated the event
    target_id: Optional[str] = None  # ID of the entity that should receive the event
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self):
        return f"Event({self.event_type.value}, {self.source_id} -> {self.target_id})"


class EventBus:
    """Event bus for managing events and subscriptions."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._target_subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        target_id: Optional[str] = None
    ):
        """Subscribe to an event type."""
        if target_id:
            # Subscribe to events for a specific target
            if target_id not in self._target_subscribers:
                self._target_subscribers[target_id] = []
            self._target_subscribers[target_id].append(callback)
        else:
            # Subscribe to all events of this type
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        target_id: Optional[str] = None
    ):
        """Unsubscribe from an event type."""
        if target_id and target_id in self._target_subscribers:
            if callback in self._target_subscribers[target_id]:
                self._target_subscribers[target_id].remove(callback)
        elif event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    async def publish(self, event: Event):
        """Publish an event."""
        await self._event_queue.put(event)

    async def process_events(self):
        """Process events from the queue."""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)

                # Notify type-based subscribers
                if event.event_type in self._subscribers:
                    for callback in self._subscribers[event.event_type]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(event)
                            else:
                                callback(event)
                        except Exception as e:
                            print(f"Error in event callback: {e}")

                # Notify target-specific subscribers
                if event.target_id and event.target_id in self._target_subscribers:
                    for callback in self._target_subscribers[event.target_id]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(event)
                            else:
                                callback(event)
                        except Exception as e:
                            print(f"Error in target callback: {e}")

                self._event_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")

    def stop(self):
        """Stop processing events."""
        self._running = False

    @property
    def pending_events(self) -> int:
        """Get the number of pending events."""
        return self._event_queue.qsize()
