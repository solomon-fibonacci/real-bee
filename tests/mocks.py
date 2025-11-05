"""
Mock objects for unit testing without external dependencies
"""
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
import asyncio


class MockDatabase:
    """Mock database for unit tests"""

    def __init__(self):
        self.data: Dict[str, Dict[int, Dict]] = defaultdict(dict)
        self.next_id: Dict[str, int] = defaultdict(lambda: 1)
        self.connected = False

    async def initialize(self):
        self.connected = True

    async def close(self):
        self.connected = False

    async def create_table(self, entity_type):
        """Mock table creation"""
        pass

    async def create(self, table_name: str, data: Dict) -> Dict:
        """Mock create operation"""
        entity_id = self.next_id[table_name]
        self.next_id[table_name] += 1

        record = {**data, "id": entity_id}
        self.data[table_name][entity_id] = record
        return record

    async def get(self, table_name: str, entity_id: int) -> Optional[Dict]:
        """Mock get operation"""
        return self.data[table_name].get(entity_id)

    async def list(
        self,
        table_name: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Mock list operation"""
        items = list(self.data[table_name].values())

        if filters:
            items = [
                item for item in items
                if all(item.get(k) == v for k, v in filters.items())
            ]

        return items[skip:skip + limit]

    async def update(
        self,
        table_name: str,
        entity_id: int,
        updates: Dict
    ) -> Optional[Dict]:
        """Mock update operation"""
        if entity_id not in self.data[table_name]:
            return None

        self.data[table_name][entity_id].update(updates)
        return self.data[table_name][entity_id]

    async def delete(self, table_name: str, entity_id: int) -> bool:
        """Mock delete operation"""
        if entity_id in self.data[table_name]:
            del self.data[table_name][entity_id]
            return True
        return False

    async def bulk_create(self, table_name: str, items: List[Dict]) -> List[Dict]:
        """Mock bulk create"""
        results = []
        for item in items:
            result = await self.create(table_name, item)
            results.append(result)
        return results

    async def count(self, table_name: str, filters: Optional[Dict] = None) -> int:
        """Mock count operation"""
        items = await self.list(table_name, filters=filters, limit=999999)
        return len(items)


class MockRedis:
    """Mock Redis for unit tests"""

    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.ttls: Dict[str, float] = {}
        self.pubsub_channels: Dict[str, List[Callable]] = defaultdict(list)
        self.connected = False

    async def initialize(self):
        self.connected = True

    async def close(self):
        self.connected = False

    async def ping(self):
        return True

    async def get(self, key: str) -> Optional[str]:
        """Mock get operation"""
        return self.data.get(key)

    async def set(self, key: str, value: Any) -> bool:
        """Mock set operation"""
        self.data[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Mock setex operation"""
        self.data[key] = value
        self.ttls[key] = ttl
        return True

    async def delete(self, *keys: str) -> int:
        """Mock delete operation"""
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
        return count

    async def exists(self, key: str) -> bool:
        """Mock exists operation"""
        return key in self.data

    async def scan_iter(self, match: str):
        """Mock scan_iter operation"""
        pattern = match.replace("*", "")
        for key in self.data.keys():
            if pattern in key:
                yield key

    async def publish(self, channel: str, message: Any):
        """Mock publish operation"""
        for callback in self.pubsub_channels.get(channel, []):
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)

    def pubsub(self):
        """Return MockPubSub instance"""
        return MockPubSub(self, ())

    async def subscribe(self, *channels: str):
        """Mock subscribe operation"""
        return MockPubSub(self, channels)

    async def incrby(self, key: str, amount: int) -> int:
        """Mock incrby operation"""
        current = int(self.data.get(key, 0))
        new_value = current + amount
        self.data[key] = str(new_value)
        return new_value

    async def decrby(self, key: str, amount: int) -> int:
        """Mock decrby operation"""
        current = int(self.data.get(key, 0))
        new_value = current - amount
        self.data[key] = str(new_value)
        return new_value

    async def flushdb(self):
        """Mock flushdb operation"""
        self.data.clear()
        self.ttls.clear()


class MockPubSub:
    """Mock Redis PubSub"""

    def __init__(self, redis: MockRedis, channels: tuple):
        self.redis = redis
        self.channels = channels
        self.messages = asyncio.Queue()

    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        pass

    async def get_message(self, ignore_subscribe_messages=False):
        """Get next message"""
        try:
            return await asyncio.wait_for(self.messages.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def close(self):
        """Close pubsub"""
        pass


class MockClipModel:
    """Mock CLIP model for testing without ML dependencies"""

    def __init__(self, dimension: int = 512):
        self.dimension = dimension

    def encode_text(self, text: str) -> List[float]:
        """Mock text encoding - deterministic based on hash"""
        import hashlib
        hash_value = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate deterministic vector
        vector = []
        for i in range(self.dimension):
            vector.append((hash_value + i) % 100 / 100.0)

        return vector

    def encode_image(self, image_url: str) -> List[float]:
        """Mock image encoding"""
        return self.encode_text(image_url)


class MockFaissIndex:
    """Mock FAISS index for testing"""

    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.vectors: List[List[float]] = []
        self.ids: List[int] = []

    def add(self, vectors: List[List[float]]):
        """Add vectors to index"""
        self.vectors.extend(vectors)

    def search(self, query_vector: List[float], k: int) -> tuple:
        """Search for similar vectors"""
        # Simple mock: return first k items
        distances = [0.9 - i * 0.1 for i in range(min(k, len(self.vectors)))]
        indices = list(range(min(k, len(self.vectors))))
        return distances, indices

    def remove_ids(self, ids: List[int]):
        """Remove vectors by ID"""
        for id_val in ids:
            if id_val in self.ids:
                idx = self.ids.index(id_val)
                del self.vectors[idx]
                del self.ids[idx]


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self):
        self.messages_sent = []
        self.messages_received = asyncio.Queue()
        self.connected = True

    async def accept(self):
        """Accept connection"""
        self.connected = True

    async def send_json(self, data: Dict):
        """Send JSON data"""
        self.messages_sent.append(data)

    async def receive_json(self) -> Dict:
        """Receive JSON data"""
        return await self.messages_received.get()

    async def close(self, code: int = 1000, reason: str = ""):
        """Close connection"""
        self.connected = False

    def add_message(self, message: Dict):
        """Add message to receive queue (for testing)"""
        self.messages_received.put_nowait(message)
