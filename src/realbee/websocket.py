"""
WebSocket connection manager for real-time updates
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from fastapi import WebSocket

from .models import WebSocketMessage, Event
from .exceptions import WebSocketException


class WebSocketManager:
    """Manages WebSocket connections and broadcasting"""

    def __init__(self, heartbeat_interval: int = 30, max_connections: int = 10000):
        self.heartbeat_interval = heartbeat_interval
        self.max_connections = max_connections

        # Track connections per entity type
        self.connections: Dict[str, List[WebSocket]] = defaultdict(list)

        # Track connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

        # Total connection count
        self.total_connections = 0

    async def connect(self, websocket: WebSocket, entity_name: str):
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            entity_name: Entity type to subscribe to

        Raises:
            WebSocketException: If max connections reached
        """
        if self.total_connections >= self.max_connections:
            await websocket.close(code=1008, reason="Maximum connections reached")
            raise WebSocketException("Maximum connections reached")

        await websocket.accept()

        self.connections[entity_name].append(websocket)
        self.connection_metadata[websocket] = {
            "entity_name": entity_name,
            "connected_at": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow(),
        }
        self.total_connections += 1

        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop(websocket, entity_name))

    def disconnect(self, websocket: WebSocket, entity_name: str):
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            entity_name: Entity type the connection was subscribed to
        """
        if websocket in self.connections[entity_name]:
            self.connections[entity_name].remove(websocket)

        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        self.total_connections -= 1

    async def broadcast_to_entity(self, entity_name: str, message: WebSocketMessage):
        """
        Broadcast message to all connections subscribed to an entity type.

        Args:
            entity_name: Entity type
            message: Message to broadcast
        """
        if entity_name not in self.connections:
            return

        # Get all active connections for this entity
        connections = self.connections[entity_name].copy()

        # Track failed connections to remove
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message.model_dump())
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, entity_name)

    async def broadcast_event(self, event: Event):
        """
        Broadcast an event to all subscribers of the entity type.

        Args:
            event: Event to broadcast
        """
        message = WebSocketMessage(type="event", data=event.model_dump())
        await self.broadcast_to_entity(event.entity_type, message)

    async def send_to_connection(self, websocket: WebSocket, message: WebSocketMessage):
        """
        Send message to a specific connection.

        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message.model_dump())
        except Exception as e:
            raise WebSocketException(f"Failed to send message: {e}")

    async def _heartbeat_loop(self, websocket: WebSocket, entity_name: str):
        """
        Send periodic heartbeat messages to keep connection alive.

        Args:
            websocket: WebSocket connection
            entity_name: Entity type
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                if websocket not in self.connection_metadata:
                    break

                # Send ping
                ping_message = WebSocketMessage(
                    type="ping", data={"timestamp": datetime.utcnow().isoformat()}
                )

                try:
                    await websocket.send_json(ping_message.model_dump())
                except Exception:
                    # Connection closed
                    self.disconnect(websocket, entity_name)
                    break

        except asyncio.CancelledError:
            pass

    async def handle_client_message(self, websocket: WebSocket, message: dict):
        """
        Handle incoming message from client.

        Args:
            websocket: WebSocket connection
            message: Parsed message from client
        """
        msg_type = message.get("type")

        if msg_type == "ping":
            # Respond with pong
            pong_message = WebSocketMessage(
                type="pong", data={"timestamp": datetime.utcnow().isoformat()}
            )
            await self.send_to_connection(websocket, pong_message)

            # Update last heartbeat
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket][
                    "last_heartbeat"
                ] = datetime.utcnow()

        elif msg_type == "pong":
            # Update last heartbeat
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket][
                    "last_heartbeat"
                ] = datetime.utcnow()

    def get_stats(self) -> Dict:
        """
        Get statistics about WebSocket connections.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_connections": self.total_connections,
            "total_rooms": len(self.connections),
            "connections_by_entity": {
                entity: len(conns) for entity, conns in self.connections.items()
            },
            "max_connections": self.max_connections,
        }

    def get_connection_info(self, websocket: WebSocket) -> Optional[Dict]:
        """
        Get information about a specific connection.

        Args:
            websocket: WebSocket connection

        Returns:
            Connection metadata or None if not found
        """
        return self.connection_metadata.get(websocket)

    async def close_all(self):
        """Close all WebSocket connections"""
        for entity_name, connections in self.connections.items():
            for connection in connections.copy():
                try:
                    await connection.close()
                except Exception:
                    pass
                self.disconnect(connection, entity_name)
