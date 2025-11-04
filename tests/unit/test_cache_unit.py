"""
Unit tests for CacheManager (using mocks)
"""
import pytest
import json

from realbee.cache import CacheManager
from realbee.core import FrameworkConfig
from tests.mocks import MockRedis


class TestCacheManagerInit:
    """Tests for CacheManager initialization"""

    def test_init_with_config(self):
        config = FrameworkConfig(redis_url="redis://localhost:6379/0")
        cache = CacheManager(config)
        assert cache.config == config
        assert cache.redis is None

    def test_init_with_custom_config(self):
        config = FrameworkConfig(
            redis_pool_size=100,
            cache_prefix="testapp"
        )
        cache = CacheManager(config)
        assert cache.config.redis_pool_size == 100
        assert cache.config.cache_prefix == "testapp"


class TestCacheKeyGeneration:
    """Tests for _make_key method"""

    def test_make_key_with_prefix(self):
        config = FrameworkConfig(cache_prefix="realbee")
        cache = CacheManager(config)
        key = cache._make_key("Product:123")
        assert key == "realbee:Product:123"

    def test_make_key_with_custom_prefix(self):
        config = FrameworkConfig(cache_prefix="myapp")
        cache = CacheManager(config)
        key = cache._make_key("User:456")
        assert key == "myapp:User:456"

    def test_make_key_empty_string(self):
        config = FrameworkConfig()
        cache = CacheManager(config)
        key = cache._make_key("")
        assert key == "realbee:"


@pytest.mark.asyncio
class TestMockCacheOperations:
    """Tests using mock Redis"""

    async def test_get_nonexistent_key(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        result = await mock_redis.get("nonexistent")
        assert result is None

    async def test_set_and_get(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        await mock_redis.set("test_key", "test_value")
        result = await mock_redis.get("test_key")
        assert result == "test_value"

    async def test_setex_with_ttl(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        await mock_redis.setex("test_key", 300, "test_value")
        result = await mock_redis.get("test_key")
        assert result == "test_value"

        # Check TTL was recorded
        assert "test_key" in mock_redis.ttls
        assert mock_redis.ttls["test_key"] == 300

    async def test_delete_existing_key(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        await mock_redis.set("test_key", "test_value")
        count = await mock_redis.delete("test_key")
        assert count == 1

        result = await mock_redis.get("test_key")
        assert result is None

    async def test_delete_nonexistent_key(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        count = await mock_redis.delete("nonexistent")
        assert count == 0

    async def test_delete_multiple_keys(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        await mock_redis.set("key1", "value1")
        await mock_redis.set("key2", "value2")
        await mock_redis.set("key3", "value3")

        count = await mock_redis.delete("key1", "key2", "key3")
        assert count == 3

    async def test_exists_true(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        await mock_redis.set("test_key", "value")
        exists = await mock_redis.exists("test_key")
        assert exists is True

    async def test_exists_false(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        exists = await mock_redis.exists("nonexistent")
        assert exists is False

    async def test_incr(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        # First increment (from 0)
        result = await mock_redis.incrby("counter", 1)
        assert result == 1

        # Second increment
        result = await mock_redis.incrby("counter", 1)
        assert result == 2

        # Increment by 5
        result = await mock_redis.incrby("counter", 5)
        assert result == 7

    async def test_decr(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        # Set initial value
        await mock_redis.set("counter", "10")

        result = await mock_redis.decrby("counter", 1)
        assert result == 9

        result = await mock_redis.decrby("counter", 5)
        assert result == 4

    async def test_scan_iter_pattern_matching(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        # Set some keys
        await mock_redis.set("product:1", "data1")
        await mock_redis.set("product:2", "data2")
        await mock_redis.set("user:1", "data3")

        # Scan for product keys
        keys = []
        async for key in mock_redis.scan_iter(match="product*"):
            keys.append(key)

        assert len(keys) == 2
        assert "product:1" in keys or "product:2" in keys

    async def test_flushdb(self):
        mock_redis = MockRedis()
        await mock_redis.initialize()

        # Set some data
        await mock_redis.set("key1", "value1")
        await mock_redis.set("key2", "value2")
        assert len(mock_redis.data) == 2

        # Flush
        await mock_redis.flushdb()
        assert len(mock_redis.data) == 0
        assert len(mock_redis.ttls) == 0


@pytest.mark.asyncio
class TestCacheManagerMethods:
    """Tests for CacheManager high-level methods"""

    async def test_cache_disabled_get_returns_none(self):
        config = FrameworkConfig(cache_enabled=False)
        cache = CacheManager(config)
        cache.redis = MockRedis()

        result = await cache.get("test_key")
        assert result is None

    async def test_cache_disabled_set_returns_false(self):
        config = FrameworkConfig(cache_enabled=False)
        cache = CacheManager(config)
        cache.redis = MockRedis()

        result = await cache.set("test_key", "value")
        assert result is False

    async def test_set_and_get_json_data(self):
        config = FrameworkConfig(cache_enabled=True)
        cache = CacheManager(config)
        cache.redis = MockRedis()
        await cache.redis.initialize()

        data = {"name": "Test", "value": 123}
        await cache.set("test_key", data)

        result = await cache.get("test_key")
        assert result == data

    async def test_set_with_custom_ttl(self):
        config = FrameworkConfig(cache_enabled=True, cache_ttl=300)
        cache = CacheManager(config)
        cache.redis = MockRedis()
        await cache.redis.initialize()

        await cache.set("test_key", "value", ttl=600)

        # Check custom TTL was used
        full_key = cache._make_key("test_key")
        assert cache.redis.ttls.get(full_key) == 600

    async def test_delete_pattern(self):
        config = FrameworkConfig()
        cache = CacheManager(config)
        cache.redis = MockRedis()
        await cache.redis.initialize()

        # Set some keys
        full_key1 = cache._make_key("Product:1")
        full_key2 = cache._make_key("Product:2")
        full_key3 = cache._make_key("User:1")

        cache.redis.data[full_key1] = "data1"
        cache.redis.data[full_key2] = "data2"
        cache.redis.data[full_key3] = "data3"

        # Delete Product keys
        count = await cache.delete_pattern("Product:*")
        assert count == 2

        # User key should still exist
        assert full_key3 in cache.redis.data

    async def test_clear_entity_cache(self):
        config = FrameworkConfig()
        cache = CacheManager(config)
        cache.redis = MockRedis()
        await cache.redis.initialize()

        # Set entity keys
        await cache.set("Product:1", {"id": 1})
        await cache.set("Product:2", {"id": 2})
        await cache.set("User:1", {"id": 1})

        # Clear Product cache
        await cache.clear_entity_cache("Product")

        # Product keys should be gone
        result = await cache.get("Product:1")
        assert result is None

        # User key should still exist
        result = await cache.get("User:1")
        assert result is not None

    async def test_publish_and_subscribe(self):
        config = FrameworkConfig()
        cache = CacheManager(config)
        cache.redis = MockRedis()
        await cache.redis.initialize()

        # Subscribe to channel
        pubsub = await cache.subscribe("test_channel")
        assert pubsub is not None

        # Publish message
        message = {"type": "test", "data": {"value": 123}}
        await cache.publish("test_channel", message)
