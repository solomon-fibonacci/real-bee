"""
Redis cache and pub/sub manager
"""
import json
from typing import Any, Dict, Optional
import redis.asyncio as redis

from .core import FrameworkConfig
from .exceptions import CacheException
from .utils import serialize_for_json


class CacheManager:
    """Manages Redis caching and pub/sub"""

    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = await redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=self.config.redis_decode_responses,
                max_connections=self.config.redis_pool_size,
            )
            # Test connection
            await self.redis.ping()
        except Exception as e:
            raise CacheException(f"Failed to initialize Redis: {e}")

    async def close(self):
        """Close Redis connection"""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.config.cache_prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.config.cache_enabled or not self.redis:
            return None

        try:
            value = await self.redis.get(self._make_key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        if not self.config.cache_enabled or not self.redis:
            return False

        try:
            ttl = ttl or self.config.cache_ttl
            serialized = json.dumps(serialize_for_json(value))
            await self.redis.setex(
                self._make_key(key),
                ttl,
                serialized
            )
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(self._make_key(key))
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.redis:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self.redis.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0

    async def clear_entity_cache(self, entity_name: str):
        """Clear all cache entries for an entity"""
        pattern = f"{entity_name}:*"
        await self.delete_pattern(pattern)

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to channel"""
        if not self.redis:
            raise CacheException("Redis not initialized")

        try:
            serialized = json.dumps(serialize_for_json(message))
            await self.redis.publish(channel, serialized)
        except Exception as e:
            raise CacheException(f"Failed to publish message: {e}")

    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        if not self.redis:
            raise CacheException("Redis not initialized")

        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(*channels)
            return self.pubsub
        except Exception as e:
            raise CacheException(f"Failed to subscribe to channels: {e}")

    async def get_message(self) -> Optional[Dict[str, Any]]:
        """Get next message from subscribed channels"""
        if not self.pubsub:
            return None

        try:
            message = await self.pubsub.get_message(ignore_subscribe_messages=True)
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, str):
                    return json.loads(data)
                return data
            return None
        except Exception as e:
            print(f"Error getting message: {e}")
            return None

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.redis:
            return 0

        try:
            return await self.redis.incrby(self._make_key(key), amount)
        except Exception as e:
            print(f"Incr error: {e}")
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        if not self.redis:
            return 0

        try:
            return await self.redis.decrby(self._make_key(key), amount)
        except Exception as e:
            print(f"Decr error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False

        try:
            return await self.redis.exists(self._make_key(key)) > 0
        except Exception as e:
            print(f"Exists error: {e}")
            return False
