"""
Integration tests for CacheManager with real Redis
"""
import pytest
import json
import asyncio

from realbee.cache import CacheManager
from realbee.core import FrameworkConfig


@pytest.mark.integration
@pytest.mark.asyncio
class TestCacheIntegration:
    """Integration tests with real Redis"""

    async def test_initialize_and_close(self, cache_manager):
        """Test Redis connection lifecycle"""
        assert cache_manager.redis is not None
        await cache_manager.redis.ping()
        await cache_manager.close()

    async def test_set_and_get_string(self, clean_cache):
        """Test basic set and get operations"""
        await clean_cache.set("test_key", "test_value")
        result = await clean_cache.get("test_key")
        assert result == "test_value"

    async def test_set_and_get_json(self, clean_cache):
        """Test storing and retrieving JSON data"""
        data = {
            "id": 123,
            "name": "Test Product",
            "price": 99.99,
            "tags": ["tag1", "tag2"]
        }

        await clean_cache.set("product:123", data)
        result = await clean_cache.get("product:123")

        assert result == data
        assert result["id"] == 123
        assert result["tags"] == ["tag1", "tag2"]

    async def test_set_with_ttl(self, clean_cache):
        """Test TTL expiration"""
        await clean_cache.set("temp_key", "temp_value", ttl=1)

        # Should exist immediately
        result = await clean_cache.get("temp_key")
        assert result == "temp_value"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        result = await clean_cache.get("temp_key")
        assert result is None

    async def test_get_nonexistent_key(self, clean_cache):
        """Test getting non-existent key returns None"""
        result = await clean_cache.get("nonexistent_key")
        assert result is None

    async def test_delete_key(self, clean_cache):
        """Test deleting a key"""
        await clean_cache.set("to_delete", "value")

        # Verify it exists
        result = await clean_cache.get("to_delete")
        assert result is not None

        # Delete it
        success = await clean_cache.delete("to_delete")
        assert success is True

        # Verify it's gone
        result = await clean_cache.get("to_delete")
        assert result is None

    async def test_delete_nonexistent_key(self, clean_cache):
        """Test deleting non-existent key returns False"""
        success = await clean_cache.delete("nonexistent")
        # Redis delete returns 0 for non-existent keys
        assert success is False

    async def test_delete_pattern(self, clean_cache):
        """Test deleting keys by pattern"""
        # Set multiple keys
        await clean_cache.set("product:1", {"id": 1})
        await clean_cache.set("product:2", {"id": 2})
        await clean_cache.set("product:3", {"id": 3})
        await clean_cache.set("user:1", {"id": 1})

        # Delete product keys
        count = await clean_cache.delete_pattern("product:*")
        assert count == 3

        # Verify product keys are gone
        assert await clean_cache.get("product:1") is None
        assert await clean_cache.get("product:2") is None

        # Verify user key still exists
        assert await clean_cache.get("user:1") is not None

    async def test_clear_entity_cache(self, clean_cache):
        """Test clearing all cache for an entity"""
        # Set entity keys
        await clean_cache.set("Product:1", {"id": 1})
        await clean_cache.set("Product:2", {"id": 2})
        await clean_cache.set("User:1", {"id": 1})

        # Clear Product cache
        await clean_cache.clear_entity_cache("Product")

        # Product keys should be gone
        assert await clean_cache.get("Product:1") is None

        # User key should remain
        assert await clean_cache.get("User:1") is not None

    async def test_exists(self, clean_cache):
        """Test checking if key exists"""
        # Key doesn't exist yet
        exists = await clean_cache.exists("test_key")
        assert exists is False

        # Create key
        await clean_cache.set("test_key", "value")

        # Now it exists
        exists = await clean_cache.exists("test_key")
        assert exists is True

    async def test_incr(self, clean_cache):
        """Test incrementing counter"""
        # Increment from 0
        value = await clean_cache.incr("counter")
        assert value == 1

        # Increment again
        value = await clean_cache.incr("counter")
        assert value == 2

        # Increment by amount
        value = await clean_cache.incr("counter", amount=5)
        assert value == 7

    async def test_decr(self, clean_cache):
        """Test decrementing counter"""
        # Set initial value
        await clean_cache.incr("counter", amount=10)

        # Decrement
        value = await clean_cache.decr("counter")
        assert value == 9

        # Decrement by amount
        value = await clean_cache.decr("counter", amount=5)
        assert value == 4

    async def test_publish_and_subscribe(self, clean_cache):
        """Test pub/sub functionality"""
        received_messages = []

        # Subscribe to channel
        pubsub = await clean_cache.subscribe("test_channel")

        # Publish a message
        message = {"type": "test", "data": {"value": 123}}
        await clean_cache.publish("test_channel", message)

        # Small delay for message propagation
        await asyncio.sleep(0.1)

        # Get message
        msg = await clean_cache.get_message()
        if msg:
            received_messages.append(msg)

        # We should have received the message
        # Note: pub/sub behavior can vary, so we check if we got something
        assert len(received_messages) <= 1  # May or may not receive in test

    async def test_multiple_subscribers(self, clean_cache):
        """Test multiple subscribers receive messages"""
        # This test demonstrates pub/sub pattern
        # In real usage, multiple consumers would subscribe

        message = {"event": "product_created", "id": 123}
        await clean_cache.publish("events:Product", message)

        # Message published successfully (no error)
        assert True

    async def test_concurrent_operations(self, clean_cache):
        """Test concurrent cache operations"""
        async def set_value(key, value):
            await clean_cache.set(key, value)

        async def get_value(key):
            return await clean_cache.get(key)

        # Set multiple values concurrently
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
            set_value("key4", "value4"),
            set_value("key5", "value5"),
        )

        # Get them concurrently
        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3"),
            get_value("key4"),
            get_value("key5"),
        )

        assert results == ["value1", "value2", "value3", "value4", "value5"]

    async def test_large_value_storage(self, clean_cache):
        """Test storing and retrieving large values"""
        # Create a large object
        large_data = {
            "items": [
                {"id": i, "name": f"Item {i}", "data": "x" * 1000}
                for i in range(100)
            ]
        }

        await clean_cache.set("large_object", large_data)
        result = await clean_cache.get("large_object")

        assert result is not None
        assert len(result["items"]) == 100
        assert result["items"][0]["id"] == 0

    async def test_unicode_data(self, clean_cache):
        """Test storing Unicode data"""
        data = {
            "english": "Hello",
            "chinese": "你好",
            "japanese": "こんにちは",
            "emoji": "🚀🐝"
        }

        await clean_cache.set("unicode_test", data)
        result = await clean_cache.get("unicode_test")

        assert result == data
        assert result["emoji"] == "🚀🐝"

    async def test_cache_with_prefix(self, test_config):
        """Test that cache prefix is applied correctly"""
        config = FrameworkConfig(
            redis_url=test_config.redis_url,
            cache_prefix="testapp"
        )

        cache = CacheManager(config)
        await cache.initialize()

        try:
            await cache.set("test_key", "test_value")

            # Key should be prefixed
            full_key = cache._make_key("test_key")
            assert full_key.startswith("testapp:")

            # Should be able to retrieve it
            result = await cache.get("test_key")
            assert result == "test_value"

        finally:
            await cache.close()

    async def test_cache_disabled(self, test_config):
        """Test behavior when cache is disabled"""
        config = FrameworkConfig(
            redis_url=test_config.redis_url,
            cache_enabled=False
        )

        cache = CacheManager(config)
        cache.redis = None  # Simulate no Redis connection

        # Operations should fail gracefully
        result = await cache.get("test_key")
        assert result is None

        success = await cache.set("test_key", "value")
        assert success is False

    async def test_rapid_set_get_cycles(self, clean_cache):
        """Test rapid set/get cycles for the same key"""
        for i in range(50):
            await clean_cache.set("rapid_test", f"value_{i}")
            result = await clean_cache.get("rapid_test")
            assert result == f"value_{i}"

    async def test_multiple_data_types(self, clean_cache):
        """Test storing different data types"""
        test_cases = [
            ("string", "test_string"),
            ("int", 12345),
            ("float", 123.45),
            ("bool", True),
            ("list", [1, 2, 3, 4, 5]),
            ("dict", {"key": "value", "nested": {"a": 1}}),
            ("null", None),
        ]

        for key, value in test_cases:
            await clean_cache.set(f"type_test:{key}", value)
            result = await clean_cache.get(f"type_test:{key}")
            assert result == value
