"""
Event bus for pub/sub system
"""
import asyncio
from typing import Callable, Dict, List, Optional
from datetime import datetime
from collections import defaultdict, deque

from .models import Event, EventType
from .cache import CacheManager
from .exceptions import EventBusException
from .utils import generate_event_id


class EventBus:
    """Manages event publishing and subscription"""

    def __init__(self, cache_manager: CacheManager, event_history_size: int = 1000):
        self.cache = cache_manager
        self.event_history_size = event_history_size
        self.event_history: deque = deque(maxlen=event_history_size)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._listening = False
        self._listen_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start listening for events"""
        if self._listening:
            return

        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self):
        """Stop listening for events"""
        self._listening = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

    async def emit(
        self,
        entity_type: str,
        event_type: EventType,
        data: dict,
        entity_id: Optional[int] = None
    ) -> Event:
        """
        Emit an event.

        Args:
            entity_type: Type of entity (e.g., "Product")
            event_type: Type of event
            data: Event payload
            entity_id: ID of the entity

        Returns:
            Created Event object
        """
        event = Event(
            id=generate_event_id(entity_type, entity_id, datetime.utcnow()),
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow()
        )

        # Add to history
        self.event_history.append(event)

        # Publish to Redis
        channel = f"events:{entity_type}"
        try:
            await self.cache.publish(channel, event.model_dump())
        except Exception as e:
            raise EventBusException(f"Failed to emit event: {e}")

        # Call local subscribers
        await self._notify_subscribers(entity_type, event_type, event)

        return event

    async def _notify_subscribers(
        self,
        entity_type: str,
        event_type: EventType,
        event: Event
    ):
        """Notify local subscribers"""
        # Notify entity-specific subscribers
        key = f"{entity_type}:{event_type.value}"
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in subscriber callback: {e}")

        # Notify wildcard subscribers (all events for this entity)
        wildcard_key = f"{entity_type}:*"
        if wildcard_key in self.subscribers:
            for callback in self.subscribers[wildcard_key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in wildcard subscriber callback: {e}")

    def on(self, entity_type: str, event_type: Optional[EventType] = None):
        """
        Decorator to subscribe to events.

        Usage:
            @event_bus.on("Product", EventType.CREATED)
            async def on_product_created(event: Event):
                print(f"Product created: {event.entity_id}")

            @event_bus.on("Product")  # Subscribe to all Product events
            async def on_product_event(event: Event):
                print(f"Product event: {event.event_type}")
        """
        def decorator(func: Callable):
            if event_type:
                key = f"{entity_type}:{event_type.value}"
            else:
                key = f"{entity_type}:*"

            self.subscribers[key].append(func)
            return func

        return decorator

    def subscribe(
        self,
        entity_type: str,
        event_type: Optional[EventType],
        callback: Callable
    ):
        """
        Subscribe to events programmatically.

        Args:
            entity_type: Type of entity
            event_type: Type of event (None for all events)
            callback: Callback function
        """
        if event_type:
            key = f"{entity_type}:{event_type.value}"
        else:
            key = f"{entity_type}:*"

        self.subscribers[key].append(callback)

    def unsubscribe(
        self,
        entity_type: str,
        event_type: Optional[EventType],
        callback: Callable
    ):
        """Unsubscribe from events"""
        if event_type:
            key = f"{entity_type}:{event_type.value}"
        else:
            key = f"{entity_type}:*"

        if key in self.subscribers and callback in self.subscribers[key]:
            self.subscribers[key].remove(callback)

    async def _listen_loop(self):
        """Background task to listen for Redis pub/sub events"""
        try:
            # Subscribe to all event channels
            pubsub = await self.cache.subscribe("events:*")

            while self._listening:
                message = await self.cache.get_message()
                if message:
                    try:
                        event = Event(**message)
                        await self._notify_subscribers(
                            event.entity_type,
                            event.event_type,
                            event
                        )
                    except Exception as e:
                        print(f"Error processing event: {e}")

                await asyncio.sleep(0.01)  # Small delay to prevent busy loop

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in event listen loop: {e}")

    def get_recent_events(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get recent events from history"""
        events = list(self.event_history)

        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]

        return events[-limit:]

    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()
