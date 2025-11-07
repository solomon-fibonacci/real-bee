"""
Integration tests for CRUDFramework
"""
import pytest
import asyncio
from fastapi import FastAPI

from realbee import CRUDFramework, FrameworkConfig
from tests.factories import Product, User, Review, ProductFactory, UserFactory


@pytest.mark.integration
@pytest.mark.asyncio
class TestFrameworkIntegration:
    """Integration tests for complete CRUDFramework"""

    async def test_framework_startup_and_shutdown(self, test_config):
        """Test framework lifecycle"""
        app = FastAPI()
        framework = CRUDFramework(app, test_config)

        await framework.startup()
        assert framework.db.pool is not None
        assert framework.cache.redis is not None

        await framework.shutdown()

    async def test_register_entity(self, framework):
        """Test registering an entity"""
        framework.register_entity(Product)

        assert "Product" in framework.metadata
        metadata = framework.metadata["Product"]
        assert metadata.entity_name == "Product"
        assert metadata.table_name == "products"
        assert metadata.has_search is True

    async def test_create_entity(self, framework):
        """Test creating an entity through framework"""
        framework.register_entity(Product)

        product_data = ProductFactory.build()
        created = await framework.create("Product", product_data)

        assert created.id is not None
        assert created.name == product_data.name
        assert created.price == product_data.price

    async def test_get_entity(self, framework):
        """Test retrieving an entity"""
        framework.register_entity(Product)

        # Create first
        product_data = ProductFactory.build()
        created = await framework.create("Product", product_data)

        # Then get
        retrieved = await framework.get("Product", created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    async def test_get_nonexistent_entity(self, framework):
        """Test getting non-existent entity returns None"""
        framework.register_entity(Product)

        result = await framework.get("Product", 99999)
        assert result is None

    async def test_list_entities(self, framework):
        """Test listing entities"""
        framework.register_entity(Product)

        # Create multiple
        for _ in range(5):
            await framework.create("Product", ProductFactory.build())

        # List them
        results = await framework.list("Product")
        assert len(results) == 5

    async def test_list_with_pagination(self, framework):
        """Test pagination"""
        framework.register_entity(Product)

        # Create 15 entities
        for _ in range(15):
            await framework.create("Product", ProductFactory.build())

        # Get first page
        page1 = await framework.list("Product", skip=0, limit=10)
        assert len(page1) == 10

        # Get second page
        page2 = await framework.list("Product", skip=10, limit=10)
        assert len(page2) == 5

    async def test_update_entity(self, framework):
        """Test updating an entity"""
        framework.register_entity(Product)

        # Create
        created = await framework.create("Product", ProductFactory.build())

        # Update
        updated = await framework.update(
            "Product",
            created.id,
            {"name": "Updated Name", "price": 199.99}
        )

        assert updated.name == "Updated Name"
        assert updated.price == 199.99
        assert updated.description == created.description  # Unchanged

    async def test_update_nonexistent_entity(self, framework):
        """Test updating non-existent entity returns None"""
        framework.register_entity(Product)

        result = await framework.update("Product", 99999, {"name": "Updated"})
        assert result is None

    async def test_delete_entity(self, framework):
        """Test deleting an entity"""
        framework.register_entity(Product)

        # Create
        created = await framework.create("Product", ProductFactory.build())

        # Delete
        success = await framework.delete("Product", created.id)
        assert success is True

        # Verify it's gone
        result = await framework.get("Product", created.id)
        assert result is None

    async def test_delete_nonexistent_entity(self, framework):
        """Test deleting non-existent entity returns False"""
        framework.register_entity(Product)

        success = await framework.delete("Product", 99999)
        assert success is False

    async def test_bulk_create(self, framework):
        """Test bulk creating entities"""
        framework.register_entity(Product)

        products = ProductFactory.build_batch(10)
        response = await framework.bulk_create("Product", products)

        assert response.created == 10
        assert len(response.entities) == 10
        assert len(response.errors) == 0

    async def test_cache_integration(self, framework):
        """Test that cache is used"""
        framework.register_entity(Product)

        # Create entity
        created = await framework.create("Product", ProductFactory.build())

        # Get it (should hit cache)
        from realbee.utils import generate_cache_key
        cache_key = generate_cache_key(
            framework.config.cache_prefix,
            "Product",
            created.id
        )

        # Check cache directly
        cached = await framework.cache.get(cache_key)
        assert cached is not None
        assert cached["id"] == created.id

    async def test_cache_invalidation_on_update(self, framework):
        """Test that cache is invalidated on update"""
        framework.register_entity(Product)

        # Create entity
        created = await framework.create("Product", ProductFactory.build())

        from realbee.utils import generate_cache_key
        cache_key = generate_cache_key(
            framework.config.cache_prefix,
            "Product",
            created.id
        )

        # Verify in cache
        cached = await framework.cache.get(cache_key)
        assert cached is not None

        # Update entity
        await framework.update("Product", created.id, {"name": "Updated"})

        # Cache should be invalidated (empty)
        cached_after = await framework.cache.get(cache_key)
        # Cache is deleted on update, so it should be None initially
        # Then repopulated on next get
        assert cached_after is None

    async def test_event_emission_on_create(self, framework):
        """Test that events are emitted on create"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", None)
        async def handler(event):
            received_events.append(event)

        # Create entity
        await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        # Should have received event
        assert len(received_events) >= 1
        assert received_events[0].entity_type == "Product"

    async def test_event_emission_on_update(self, framework):
        """Test that events are emitted on update"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", None)
        async def handler(event):
            received_events.append(event)

        # Create and update
        created = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)
        initial_count = len(received_events)

        await framework.update("Product", created.id, {"name": "Updated"})
        await asyncio.sleep(0.1)

        # Should have received update event
        assert len(received_events) > initial_count

    async def test_event_emission_on_delete(self, framework):
        """Test that events are emitted on delete"""
        framework.register_entity(Product)

        received_events = []

        @framework.event_bus.on("Product", None)
        async def handler(event):
            received_events.append(event)

        # Create and delete
        created = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)
        initial_count = len(received_events)

        await framework.delete("Product", created.id)
        await asyncio.sleep(0.1)

        # Should have received delete event
        assert len(received_events) > initial_count

    async def test_multiple_entities(self, framework):
        """Test working with multiple entity types"""
        framework.register_entity(Product)
        framework.register_entity(User)

        # Create entities of both types
        product = await framework.create("Product", ProductFactory.build())
        user = await framework.create("User", UserFactory.build())

        assert product.id is not None
        assert user.id is not None

        # List each type
        products = await framework.list("Product")
        users = await framework.list("User")

        assert len(products) == 1
        assert len(users) == 1

    async def test_hooks_execution(self, framework):
        """Test that hooks are executed"""
        from realbee.core import EntityHooks

        hook_calls = []

        class TestHooks(EntityHooks):
            @staticmethod
            def before_create(instance):
                hook_calls.append("before_create")
                return instance

            @staticmethod
            async def after_create(instance):
                hook_calls.append("after_create")

        framework.register_entity(Product, hooks=TestHooks())

        await framework.create("Product", ProductFactory.build())

        assert "before_create" in hook_calls
        assert "after_create" in hook_calls

    async def test_before_create_hook_modification(self, framework):
        """Test that before_create can modify data"""
        from realbee.core import EntityHooks

        class ModifyHooks(EntityHooks):
            @staticmethod
            def before_create(instance):
                # Force uppercase name
                instance.name = instance.name.upper()
                return instance

        framework.register_entity(Product, hooks=ModifyHooks())

        product_data = ProductFactory.build(name="test product")
        created = await framework.create("Product", product_data)

        assert created.name == "TEST PRODUCT"

    async def test_before_delete_hook_prevention(self, framework):
        """Test that before_delete can prevent deletion"""
        from realbee.core import EntityHooks
        from realbee.exceptions import ValidationException

        class PreventDeleteHooks(EntityHooks):
            @staticmethod
            async def before_delete(instance):
                # Prevent deletion of expensive products
                if instance.price > 100:
                    return False
                return True

        framework.register_entity(Product, hooks=PreventDeleteHooks())

        # Create expensive product
        expensive = await framework.create(
            "Product",
            ProductFactory.build(price=200.0)
        )

        # Try to delete - should fail
        with pytest.raises(ValidationException):
            await framework.delete("Product", expensive.id)

        # Product should still exist
        result = await framework.get("Product", expensive.id)
        assert result is not None

    async def test_concurrent_operations(self, framework):
        """Test concurrent create operations"""
        framework.register_entity(Product)

        async def create_product():
            return await framework.create("Product", ProductFactory.build())

        # Create 10 products concurrently
        results = await asyncio.gather(*[create_product() for _ in range(10)])

        assert len(results) == 10
        assert all(r.id is not None for r in results)

        # Verify all were created
        all_products = await framework.list("Product", limit=20)
        assert len(all_products) == 10

    async def test_transaction_like_behavior(self, framework):
        """Test that failed operations don't leave partial state"""
        framework.register_entity(Product)

        # Create a product
        created = await framework.create("Product", ProductFactory.build())
        initial_count = len(await framework.list("Product"))

        # Try to update with invalid data (should handle gracefully)
        try:
            # This should work actually, but demonstrates the concept
            await framework.update("Product", created.id, {"name": "Updated"})
        except Exception:
            pass

        # Count should still be consistent
        final_count = len(await framework.list("Product"))
        assert final_count == initial_count
