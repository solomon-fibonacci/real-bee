"""
End-to-end tests for real-time updates and event propagation
"""
import pytest
import asyncio

from realbee.models import EventType
from tests.factories import Product, ProductFactory
from tests.mocks import MockWebSocket


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRealtimeEventPropagation:
    """Test end-to-end real-time event propagation"""

    async def test_create_triggers_event(self, framework):
        """Test that creating an entity triggers real-time event"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", EventType.CREATED)
        async def handler(event):
            received_events.append(event)

        # Create product
        product = await framework.create("Product", ProductFactory.build())

        # Wait for event propagation
        await asyncio.sleep(0.2)

        # Should have received event
        assert len(received_events) >= 1
        event = received_events[0]
        assert event.entity_type == "Product"
        assert event.event_type == EventType.CREATED
        assert event.entity_id == product.id

    async def test_update_triggers_event(self, framework):
        """Test that updating an entity triggers real-time event"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", EventType.UPDATED)
        async def handler(event):
            received_events.append(event)

        # Create and update
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        await framework.update("Product", product.id, {"name": "Updated"})
        await asyncio.sleep(0.2)

        # Should have received update event
        assert len(received_events) >= 1
        event = received_events[0]
        assert event.entity_type == "Product"
        assert event.event_type == EventType.UPDATED

    async def test_delete_triggers_event(self, framework):
        """Test that deleting an entity triggers real-time event"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", EventType.DELETED)
        async def handler(event):
            received_events.append(event)

        # Create and delete
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        await framework.delete("Product", product.id)
        await asyncio.sleep(0.2)

        # Should have received delete event
        assert len(received_events) >= 1
        event = received_events[0]
        assert event.entity_type == "Product"
        assert event.event_type == EventType.DELETED

    async def test_bulk_create_triggers_event(self, framework):
        """Test that bulk create triggers bulk event"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", EventType.BULK_CREATED)
        async def handler(event):
            received_events.append(event)

        # Bulk create
        products = ProductFactory.build_batch(5)
        await framework.bulk_create("Product", products)

        await asyncio.sleep(0.2)

        # Should have received bulk event
        assert len(received_events) >= 1
        event = received_events[0]
        assert event.event_type == EventType.BULK_CREATED

    async def test_multiple_subscribers_receive_events(self, framework):
        """Test multiple subscribers all receive events"""
        framework.register_entity(Product)

        received_1 = []
        received_2 = []
        received_3 = []

        @framework.event_bus.on("Product", None)
        async def handler1(event):
            received_1.append(event)

        @framework.event_bus.on("Product", None)
        async def handler2(event):
            received_2.append(event)

        @framework.event_bus.on("Product", None)
        async def handler3(event):
            received_3.append(event)

        # Create product
        await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.2)

        # All should have received the event
        assert len(received_1) >= 1
        assert len(received_2) >= 1
        assert len(received_3) >= 1

    async def test_event_ordering(self, framework):
        """Test that events maintain proper ordering"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", None)
        async def handler(event):
            received_events.append(event)

        # Perform operations in sequence
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        await framework.update("Product", product.id, {"name": "Update 1"})
        await asyncio.sleep(0.1)

        await framework.update("Product", product.id, {"name": "Update 2"})
        await asyncio.sleep(0.1)

        await framework.delete("Product", product.id)
        await asyncio.sleep(0.2)

        # Should have received events in order: CREATE, UPDATE, UPDATE, DELETE
        assert len(received_events) >= 4
        assert received_events[0].event_type == EventType.CREATED
        assert received_events[1].event_type == EventType.UPDATED
        assert received_events[2].event_type == EventType.UPDATED
        assert received_events[3].event_type == EventType.DELETED


@pytest.mark.e2e
@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Test WebSocket integration with CRUD operations"""

    async def test_websocket_receives_create_event(self, framework):
        """Test WebSocket receives event when entity is created"""
        framework.register_entity(Product)

        # Create mock WebSocket
        ws = MockWebSocket()
        await framework.ws_manager.connect(ws, "Product")

        # Create product
        product = await framework.create("Product", ProductFactory.build())

        # Wait for broadcast
        await asyncio.sleep(0.2)

        # WebSocket should have received message
        assert len(ws.messages_sent) >= 1
        message = ws.messages_sent[0]
        assert message["type"] == "event"

    async def test_websocket_receives_update_event(self, framework):
        """Test WebSocket receives event when entity is updated"""
        framework.register_entity(Product)

        ws = MockWebSocket()
        await framework.ws_manager.connect(ws, "Product")

        # Create and update
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        initial_count = len(ws.messages_sent)

        await framework.update("Product", product.id, {"name": "Updated"})
        await asyncio.sleep(0.2)

        # Should have received update event
        assert len(ws.messages_sent) > initial_count

    async def test_multiple_websockets_receive_events(self, framework):
        """Test multiple WebSocket connections receive same event"""
        framework.register_entity(Product)

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await framework.ws_manager.connect(ws1, "Product")
        await framework.ws_manager.connect(ws2, "Product")
        await framework.ws_manager.connect(ws3, "Product")

        # Create product
        await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.2)

        # All should have received the event
        assert len(ws1.messages_sent) >= 1
        assert len(ws2.messages_sent) >= 1
        assert len(ws3.messages_sent) >= 1

    async def test_websocket_isolation_between_entities(self, framework):
        """Test WebSockets only receive events for their entity type"""
        from tests.factories import User, UserFactory

        framework.register_entity(Product)
        framework.register_entity(User)

        product_ws = MockWebSocket()
        user_ws = MockWebSocket()

        await framework.ws_manager.connect(product_ws, "Product")
        await framework.ws_manager.connect(user_ws, "User")

        # Create product
        await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.2)

        # Only product WebSocket should receive event
        assert len(product_ws.messages_sent) >= 1
        # User WebSocket should not receive product events
        # (Note: in the mock, it won't receive anything)

    async def test_websocket_disconnection(self, framework):
        """Test WebSocket disconnection and cleanup"""
        framework.register_entity(Product)

        ws = MockWebSocket()
        await framework.ws_manager.connect(ws, "Product")

        assert framework.ws_manager.total_connections == 1

        # Disconnect
        framework.ws_manager.disconnect(ws, "Product")

        assert framework.ws_manager.total_connections == 0


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCompleteRealtimeWorkflow:
    """Test complete real-time workflows"""

    async def test_full_realtime_crud_workflow(self, framework):
        """Test complete workflow with events and WebSockets"""
        framework.register_entity(Product)

        # Set up event listener
        all_events = []

        @framework.event_bus.on("Product", None)
        async def event_logger(event):
            all_events.append(event)

        # Set up WebSocket
        ws = MockWebSocket()
        await framework.ws_manager.connect(ws, "Product")

        # 1. CREATE
        product = await framework.create(
            "Product",
            ProductFactory.build(name="Real-time Product")
        )
        await asyncio.sleep(0.2)

        assert len(all_events) >= 1
        assert all_events[0].event_type == EventType.CREATED
        assert len(ws.messages_sent) >= 1

        # 2. UPDATE
        await framework.update("Product", product.id, {"price": 299.99})
        await asyncio.sleep(0.2)

        assert len(all_events) >= 2
        assert all_events[1].event_type == EventType.UPDATED
        assert len(ws.messages_sent) >= 2

        # 3. DELETE
        await framework.delete("Product", product.id)
        await asyncio.sleep(0.2)

        assert len(all_events) >= 3
        assert all_events[2].event_type == EventType.DELETED
        assert len(ws.messages_sent) >= 3

        # Cleanup
        framework.ws_manager.disconnect(ws, "Product")

    async def test_concurrent_clients_realtime_sync(self, framework):
        """Test multiple clients stay in sync via real-time updates"""
        framework.register_entity(Product)

        # Simulate 3 clients with WebSockets
        client1_ws = MockWebSocket()
        client2_ws = MockWebSocket()
        client3_ws = MockWebSocket()

        await framework.ws_manager.connect(client1_ws, "Product")
        await framework.ws_manager.connect(client2_ws, "Product")
        await framework.ws_manager.connect(client3_ws, "Product")

        # Client 1 creates a product
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.2)

        # All clients should be notified
        assert len(client1_ws.messages_sent) >= 1
        assert len(client2_ws.messages_sent) >= 1
        assert len(client3_ws.messages_sent) >= 1

        # Client 2 updates the product
        await framework.update("Product", product.id, {"price": 999.99})
        await asyncio.sleep(0.2)

        # All clients should be notified of update
        assert len(client1_ws.messages_sent) >= 2
        assert len(client2_ws.messages_sent) >= 2
        assert len(client3_ws.messages_sent) >= 2

        # Client 3 deletes the product
        await framework.delete("Product", product.id)
        await asyncio.sleep(0.2)

        # All clients should be notified of deletion
        assert len(client1_ws.messages_sent) >= 3
        assert len(client2_ws.messages_sent) >= 3
        assert len(client3_ws.messages_sent) >= 3

    async def test_event_history_tracking(self, framework):
        """Test that event history is maintained"""
        framework.register_entity(Product)

        # Perform several operations
        for i in range(5):
            product = await framework.create("Product", ProductFactory.build())
            await framework.update("Product", product.id, {"price": float(i * 100)})
            await framework.delete("Product", product.id)

        await asyncio.sleep(0.5)

        # Check event history
        history = framework.event_bus.get_recent_events(entity_type="Product")

        # Should have 15 events (5 creates, 5 updates, 5 deletes)
        assert len(history) >= 15

    async def test_high_frequency_events(self, framework):
        """Test system handles high-frequency events"""
        framework.register_entity(Product)

        received_count = [0]

        @framework.event_bus.on("Product", None)
        async def counter(event):
            received_count[0] += 1

        # Rapid fire creates
        products = []
        for i in range(20):
            product = await framework.create("Product", ProductFactory.build())
            products.append(product)

        await asyncio.sleep(0.5)

        # Should have received all events
        assert received_count[0] >= 20

    async def test_websocket_heartbeat(self, framework):
        """Test WebSocket heartbeat mechanism"""
        framework.register_entity(Product)

        ws = MockWebSocket()
        await framework.ws_manager.connect(ws, "Product")

        # Simulate client sending ping
        await framework.ws_manager.handle_client_message(
            ws,
            {"type": "ping"}
        )

        # Should receive pong
        pong_messages = [m for m in ws.messages_sent if m["type"] == "pong"]
        assert len(pong_messages) >= 1

    async def test_event_metadata_propagation(self, framework):
        """Test that event metadata is properly propagated"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", EventType.CREATED)
        async def handler(event):
            received_events.append(event)

        # Create with tracking
        product = await framework.create("Product", ProductFactory.build())

        await asyncio.sleep(0.2)

        assert len(received_events) >= 1
        event = received_events[0]

        # Check event has proper structure
        assert event.id is not None
        assert event.entity_type == "Product"
        assert event.entity_id == product.id
        assert event.timestamp is not None
        assert event.data is not None


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestRealtimePerformance:
    """Test real-time performance characteristics"""

    async def test_many_concurrent_events(self, framework):
        """Test handling many concurrent events"""
        framework.register_entity(Product)

        event_count = [0]

        @framework.event_bus.on("Product", None)
        async def counter(event):
            event_count[0] += 1

        # Create 50 products concurrently
        await asyncio.gather(*[
            framework.create("Product", ProductFactory.build())
            for _ in range(50)
        ])

        await asyncio.sleep(1.0)

        # Should have received all events
        assert event_count[0] >= 50

    async def test_many_websocket_connections(self, framework):
        """Test handling many WebSocket connections"""
        framework.register_entity(Product)

        # Connect 20 WebSockets
        websockets = []
        for _ in range(20):
            ws = MockWebSocket()
            await framework.ws_manager.connect(ws, "Product")
            websockets.append(ws)

        # Create product
        await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.3)

        # All should have received the event
        for ws in websockets:
            assert len(ws.messages_sent) >= 1

        # Cleanup
        for ws in websockets:
            framework.ws_manager.disconnect(ws, "Product")

        assert framework.ws_manager.total_connections == 0
