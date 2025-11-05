"""
Integration tests for EventBus with real Redis
"""
import pytest
import asyncio

from realbee.events import EventBus
from realbee.models import EventType


@pytest.mark.integration
@pytest.mark.asyncio
class TestEventBusIntegration:
    """Integration tests for EventBus with real Redis"""

    async def test_emit_event(self, event_bus):
        """Test emitting an event"""
        event = await event_bus.emit(
            entity_type="Product",
            event_type=EventType.CREATED,
            data={"id": 1, "name": "Test Product"},
            entity_id=1
        )

        assert event.id is not None
        assert event.entity_type == "Product"
        assert event.event_type == EventType.CREATED
        assert event.entity_id == 1
        assert event.data == {"id": 1, "name": "Test Product"}

    async def test_event_stored_in_history(self, event_bus):
        """Test that emitted events are stored in history"""
        await event_bus.emit(
            entity_type="Product",
            event_type=EventType.CREATED,
            data={"id": 1},
            entity_id=1
        )

        history = event_bus.get_recent_events()
        assert len(history) >= 1
        assert history[-1].entity_type == "Product"

    async def test_subscribe_to_specific_event(self, event_bus):
        """Test subscribing to specific event type"""
        received_events = []

        @event_bus.on("Product", EventType.CREATED)
        async def handler(event):
            received_events.append(event)

        # Emit event
        await event_bus.emit(
            entity_type="Product",
            event_type=EventType.CREATED,
            data={"id": 1},
            entity_id=1
        )

        # Small delay for event propagation
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].entity_type == "Product"

    async def test_subscribe_to_all_entity_events(self, event_bus):
        """Test subscribing to all events for an entity"""
        received_events = []

        @event_bus.on("Product")  # No event_type = all events
        async def handler(event):
            received_events.append(event)

        # Emit different event types
        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await event_bus.emit("Product", EventType.UPDATED, {"id": 1}, 1)
        await event_bus.emit("Product", EventType.DELETED, {"id": 1}, 1)

        await asyncio.sleep(0.1)

        assert len(received_events) == 3

    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers receive same event"""
        received_1 = []
        received_2 = []

        @event_bus.on("Product", EventType.CREATED)
        async def handler1(event):
            received_1.append(event)

        @event_bus.on("Product", EventType.CREATED)
        async def handler2(event):
            received_2.append(event)

        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await asyncio.sleep(0.1)

        assert len(received_1) == 1
        assert len(received_2) == 1

    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events"""
        received_events = []

        async def handler(event):
            received_events.append(event)

        # Subscribe
        event_bus.subscribe("Product", EventType.CREATED, handler)

        # Emit event - should receive
        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1

        # Unsubscribe
        event_bus.unsubscribe("Product", EventType.CREATED, handler)

        # Emit again - should not receive
        await event_bus.emit("Product", EventType.CREATED, {"id": 2}, 2)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1  # Still 1

    async def test_event_history_limit(self, clean_cache):
        """Test that event history respects size limit"""
        bus = EventBus(clean_cache, event_history_size=5)
        await bus.start()

        try:
            # Emit more events than history size
            for i in range(10):
                await bus.emit("Product", EventType.CREATED, {"id": i}, i)

            history = bus.get_recent_events()
            assert len(history) <= 5

        finally:
            await bus.stop()

    async def test_get_recent_events_filtered(self, event_bus):
        """Test getting recent events filtered by entity type"""
        # Emit events for different entities
        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await event_bus.emit("User", EventType.CREATED, {"id": 1}, 1)
        await event_bus.emit("Product", EventType.UPDATED, {"id": 1}, 1)

        # Get only Product events
        product_events = event_bus.get_recent_events(entity_type="Product")

        assert len(product_events) == 2
        assert all(e.entity_type == "Product" for e in product_events)

    async def test_get_recent_events_with_limit(self, event_bus):
        """Test limiting number of recent events returned"""
        # Emit several events
        for i in range(10):
            await event_bus.emit("Product", EventType.CREATED, {"id": i}, i)

        # Get only last 5
        events = event_bus.get_recent_events(limit=5)
        assert len(events) == 5

    async def test_clear_history(self, event_bus):
        """Test clearing event history"""
        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await event_bus.emit("Product", EventType.CREATED, {"id": 2}, 2)

        history = event_bus.get_recent_events()
        assert len(history) >= 2

        event_bus.clear_history()

        history = event_bus.get_recent_events()
        assert len(history) == 0

    async def test_concurrent_event_emission(self, event_bus):
        """Test emitting events concurrently"""
        async def emit_event(i):
            await event_bus.emit("Product", EventType.CREATED, {"id": i}, i)

        # Emit 20 events concurrently
        await asyncio.gather(*[emit_event(i) for i in range(20)])

        history = event_bus.get_recent_events()
        assert len(history) >= 20

    async def test_event_with_metadata(self, event_bus):
        """Test events with additional metadata"""
        event = await event_bus.emit(
            entity_type="Product",
            event_type=EventType.CREATED,
            data={"id": 1, "name": "Test"},
            entity_id=1
        )

        # Add metadata to event data
        event.metadata = {"user_id": 123, "ip": "192.168.1.1"}

        assert event.metadata["user_id"] == 123

    async def test_event_ordering(self, event_bus):
        """Test that events maintain order"""
        # Emit events in sequence
        for i in range(5):
            await event_bus.emit("Product", EventType.CREATED, {"id": i}, i)
            await asyncio.sleep(0.01)  # Small delay

        events = event_bus.get_recent_events(entity_type="Product")

        # Check timestamps are increasing
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    async def test_different_event_types(self, event_bus):
        """Test all event types work correctly"""
        event_types = [
            EventType.CREATED,
            EventType.UPDATED,
            EventType.DELETED,
            EventType.BULK_CREATED
        ]

        for event_type in event_types:
            event = await event_bus.emit("Product", event_type, {"id": 1}, 1)
            assert event.event_type == event_type

    async def test_event_bus_start_stop(self, clean_cache):
        """Test starting and stopping event bus"""
        bus = EventBus(clean_cache, event_history_size=100)

        assert bus._listening is False

        await bus.start()
        assert bus._listening is True

        await bus.stop()
        assert bus._listening is False

    async def test_sync_callback_handler(self, event_bus):
        """Test that synchronous callbacks also work"""
        received_events = []

        # Synchronous handler (not async)
        def sync_handler(event):
            received_events.append(event)

        event_bus.subscribe("Product", EventType.CREATED, sync_handler)

        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await asyncio.sleep(0.1)

        assert len(received_events) == 1

    async def test_handler_exception_doesnt_break_bus(self, event_bus):
        """Test that exceptions in handlers don't break the event bus"""
        received_good = []

        @event_bus.on("Product", EventType.CREATED)
        async def bad_handler(event):
            raise Exception("Handler error!")

        @event_bus.on("Product", EventType.CREATED)
        async def good_handler(event):
            received_good.append(event)

        # Emit event - bad handler will raise, but good handler should still work
        await event_bus.emit("Product", EventType.CREATED, {"id": 1}, 1)
        await asyncio.sleep(0.1)

        assert len(received_good) == 1
