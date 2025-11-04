"""
Unit tests for WebSocketManager
"""
import pytest
from datetime import datetime

from realbee.websocket import WebSocketManager
from realbee.models import WebSocketMessage, Event, EventType
from realbee.exceptions import WebSocketException
from tests.mocks import MockWebSocket


class TestWebSocketManagerInit:
    """Tests for WebSocketManager initialization"""

    def test_init_with_defaults(self):
        manager = WebSocketManager()
        assert manager.heartbeat_interval == 30
        assert manager.max_connections == 10000
        assert manager.total_connections == 0
        assert len(manager.connections) == 0

    def test_init_with_custom_values(self):
        manager = WebSocketManager(heartbeat_interval=60, max_connections=5000)
        assert manager.heartbeat_interval == 60
        assert manager.max_connections == 5000


@pytest.mark.asyncio
class TestWebSocketConnection:
    """Tests for WebSocket connection management"""

    async def test_connect_websocket(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        assert ws.connected is True
        assert manager.total_connections == 1
        assert ws in manager.connections["Product"]
        assert ws in manager.connection_metadata

    async def test_connect_metadata(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        metadata = manager.connection_metadata[ws]
        assert metadata["entity_name"] == "Product"
        assert "connected_at" in metadata
        assert "last_heartbeat" in metadata
        assert isinstance(metadata["connected_at"], datetime)

    async def test_connect_max_connections_reached(self):
        manager = WebSocketManager(max_connections=2)

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "Product")

        # Third connection should fail
        with pytest.raises(WebSocketException):
            await manager.connect(ws3, "Product")

    async def test_disconnect_websocket(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")
        assert manager.total_connections == 1

        manager.disconnect(ws, "Product")
        assert manager.total_connections == 0
        assert ws not in manager.connections["Product"]
        assert ws not in manager.connection_metadata

    async def test_disconnect_removes_from_correct_entity(self):
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "User")

        manager.disconnect(ws1, "Product")

        assert ws1 not in manager.connections["Product"]
        assert ws2 in manager.connections["User"]
        assert manager.total_connections == 1


@pytest.mark.asyncio
class TestWebSocketBroadcasting:
    """Tests for broadcasting messages"""

    async def test_broadcast_to_entity(self):
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "Product")

        message = WebSocketMessage(type="event", data={"test": "value"})
        await manager.broadcast_to_entity("Product", message)

        assert len(ws1.messages_sent) == 1
        assert len(ws2.messages_sent) == 1
        assert ws1.messages_sent[0]["type"] == "event"

    async def test_broadcast_to_nonexistent_entity(self):
        manager = WebSocketManager()

        message = WebSocketMessage(type="event", data={})
        # Should not raise error
        await manager.broadcast_to_entity("NonExistent", message)

    async def test_broadcast_removes_failed_connections(self):
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "Product")

        # Simulate ws1 failure by marking it disconnected
        ws1.connected = False

        # Override send_json to raise exception for ws1
        async def failing_send(data):
            raise Exception("Connection closed")

        ws1.send_json = failing_send

        message = WebSocketMessage(type="event", data={})
        await manager.broadcast_to_entity("Product", message)

        # ws1 should be removed, ws2 should remain
        assert ws1 not in manager.connections["Product"]
        assert ws2 in manager.connections["Product"]

    async def test_broadcast_event(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        event = Event(
            id="test-123",
            entity_type="Product",
            entity_id=1,
            event_type=EventType.CREATED,
            data={"name": "Test Product"}
        )

        await manager.broadcast_event(event)

        assert len(ws.messages_sent) == 1
        assert ws.messages_sent[0]["type"] == "event"
        assert "data" in ws.messages_sent[0]

    async def test_send_to_specific_connection(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        message = WebSocketMessage(type="ping")
        await manager.send_to_connection(ws, message)

        assert len(ws.messages_sent) == 1
        assert ws.messages_sent[0]["type"] == "ping"

    async def test_send_to_connection_failure(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        # Simulate failure
        async def failing_send(data):
            raise Exception("Connection failed")

        ws.send_json = failing_send

        message = WebSocketMessage(type="ping")

        with pytest.raises(WebSocketException):
            await manager.send_to_connection(ws, message)


@pytest.mark.asyncio
class TestWebSocketMessages:
    """Tests for handling client messages"""

    async def test_handle_ping_message(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        await manager.handle_client_message(ws, {"type": "ping"})

        # Should send pong response
        assert len(ws.messages_sent) == 1
        assert ws.messages_sent[0]["type"] == "pong"

    async def test_handle_pong_message(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")
        initial_heartbeat = manager.connection_metadata[ws]["last_heartbeat"]

        # Small delay to ensure timestamp changes
        import asyncio
        await asyncio.sleep(0.01)

        await manager.handle_client_message(ws, {"type": "pong"})

        # Last heartbeat should be updated
        updated_heartbeat = manager.connection_metadata[ws]["last_heartbeat"]
        assert updated_heartbeat > initial_heartbeat

    async def test_ping_updates_heartbeat(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")
        initial_heartbeat = manager.connection_metadata[ws]["last_heartbeat"]

        import asyncio
        await asyncio.sleep(0.01)

        await manager.handle_client_message(ws, {"type": "ping"})

        updated_heartbeat = manager.connection_metadata[ws]["last_heartbeat"]
        assert updated_heartbeat > initial_heartbeat


class TestWebSocketStats:
    """Tests for WebSocket statistics"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        manager = WebSocketManager()
        stats = manager.get_stats()

        assert stats["total_connections"] == 0
        assert stats["total_rooms"] == 0
        assert stats["connections_by_entity"] == {}
        assert stats["max_connections"] == 10000

    @pytest.mark.asyncio
    async def test_get_stats_with_connections(self):
        manager = WebSocketManager()

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "Product")
        await manager.connect(ws3, "User")

        stats = manager.get_stats()

        assert stats["total_connections"] == 3
        assert stats["total_rooms"] == 2
        assert stats["connections_by_entity"]["Product"] == 2
        assert stats["connections_by_entity"]["User"] == 1

    @pytest.mark.asyncio
    async def test_get_connection_info(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        await manager.connect(ws, "Product")

        info = manager.get_connection_info(ws)
        assert info is not None
        assert info["entity_name"] == "Product"
        assert "connected_at" in info

    @pytest.mark.asyncio
    async def test_get_connection_info_nonexistent(self):
        manager = WebSocketManager()
        ws = MockWebSocket()

        info = manager.get_connection_info(ws)
        assert info is None


@pytest.mark.asyncio
class TestWebSocketCleanup:
    """Tests for WebSocket cleanup operations"""

    async def test_close_all_connections(self):
        manager = WebSocketManager()

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1, "Product")
        await manager.connect(ws2, "Product")
        await manager.connect(ws3, "User")

        assert manager.total_connections == 3

        await manager.close_all()

        assert manager.total_connections == 0
        assert len(manager.connections["Product"]) == 0
        assert len(manager.connections["User"]) == 0
        assert ws1.connected is False
        assert ws2.connected is False
        assert ws3.connected is False
