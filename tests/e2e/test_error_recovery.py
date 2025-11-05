"""
End-to-end tests for error recovery and resilience
"""
import pytest
import asyncio

from realbee.exceptions import (
    EntityNotFoundException,
    ValidationException,
)
from realbee.core import EntityHooks
from tests.factories import Product, ProductFactory


@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling across the system"""

    async def test_entity_not_found_handling(self, framework):
        """Test handling of non-existent entity operations"""
        framework.register_entity(Product)

        # Get non-existent
        result = await framework.get("Product", 99999)
        assert result is None

        # Update non-existent
        result = await framework.update("Product", 99999, {"name": "Test"})
        assert result is None

        # Delete non-existent
        result = await framework.delete("Product", 99999)
        assert result is False

    async def test_unregistered_entity_error(self, framework):
        """Test operations on unregistered entities raise appropriate errors"""
        with pytest.raises(EntityNotFoundException):
            await framework.create("UnregisteredEntity", {"name": "Test"})

        with pytest.raises(EntityNotFoundException):
            await framework.get("UnregisteredEntity", 1)

    async def test_hook_validation_error(self, framework):
        """Test that hook validation errors are properly handled"""

        class StrictHooks(EntityHooks):
            @staticmethod
            def before_create(instance):
                if instance.price < 10:
                    raise ValidationException("Price too low")
                return instance

        framework.register_entity(Product, hooks=StrictHooks())

        # Should raise validation error
        with pytest.raises(ValidationException):
            await framework.create(
                "Product",
                ProductFactory.build(price=5.0)
            )

        # Valid price should work
        result = await framework.create(
            "Product",
            ProductFactory.build(price=20.0)
        )
        assert result.id is not None

    async def test_before_delete_prevention(self, framework):
        """Test that before_delete hook can prevent deletion"""

        class ProtectedHooks(EntityHooks):
            @staticmethod
            async def before_delete(instance):
                # Prevent deletion of expensive items
                return instance.price < 1000

        framework.register_entity(Product, hooks=ProtectedHooks())

        # Create expensive product
        expensive = await framework.create(
            "Product",
            ProductFactory.build(price=1500.0)
        )

        # Try to delete - should fail
        with pytest.raises(ValidationException):
            await framework.delete("Product", expensive.id)

        # Product should still exist
        exists = await framework.get("Product", expensive.id)
        assert exists is not None

        # Create cheap product
        cheap = await framework.create(
            "Product",
            ProductFactory.build(price=50.0)
        )

        # Should be able to delete
        success = await framework.delete("Product", cheap.id)
        assert success is True


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRecoveryScenarios:
    """Test system recovery from various scenarios"""

    async def test_recovery_after_failed_operation(self, framework):
        """Test system recovers after failed operation"""
        framework.register_entity(Product)

        # Create product successfully
        product1 = await framework.create("Product", ProductFactory.build())
        assert product1.id is not None

        # Try invalid operation
        result = await framework.get("Product", 99999)
        assert result is None

        # System should still work normally
        product2 = await framework.create("Product", ProductFactory.build())
        assert product2.id is not None

        all_products = await framework.list("Product")
        assert len(all_products) == 2

    async def test_concurrent_access_consistency(self, framework):
        """Test data consistency under concurrent access"""
        framework.register_entity(Product)

        # Create initial product
        product = await framework.create("Product", ProductFactory.build())

        # Concurrent reads
        results = await asyncio.gather(*[
            framework.get("Product", product.id)
            for _ in range(10)
        ])

        # All should return the same product
        assert all(r is not None for r in results)
        assert all(r.id == product.id for r in results)

    async def test_rapid_create_delete_cycles(self, framework):
        """Test system handles rapid create-delete cycles"""
        framework.register_entity(Product)

        for i in range(20):
            product = await framework.create("Product", ProductFactory.build())
            await framework.delete("Product", product.id)

        # System should be stable
        products = await framework.list("Product")
        assert len(products) == 0

    async def test_update_race_condition_handling(self, framework):
        """Test handling of concurrent updates to same entity"""
        framework.register_entity(Product)

        product = await framework.create("Product", ProductFactory.build())

        # Concurrent updates
        await asyncio.gather(
            framework.update("Product", product.id, {"name": "Name A"}),
            framework.update("Product", product.id, {"name": "Name B"}),
            framework.update("Product", product.id, {"name": "Name C"}),
        )

        # Final state should be consistent
        final = await framework.get("Product", product.id)
        assert final is not None
        assert final.name in ["Name A", "Name B", "Name C"]  # Last write wins


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDataConsistency:
    """Test data consistency across operations"""

    async def test_cache_db_consistency(self, framework):
        """Test cache and database stay in sync"""
        framework.register_entity(Product)

        # Create product
        product = await framework.create("Product", ProductFactory.build())

        # Get from cache (via framework)
        cached = await framework.get("Product", product.id)
        assert cached is not None

        # Update
        await framework.update("Product", product.id, {"name": "Updated"})

        # Get again - should have new data
        updated = await framework.get("Product", product.id)
        assert updated.name == "Updated"

        # Delete
        await framework.delete("Product", product.id)

        # Should be gone from both cache and DB
        deleted = await framework.get("Product", product.id)
        assert deleted is None

    async def test_event_cache_consistency(self, framework):
        """Test events reflect cache state changes"""
        framework.register_entity(Product)

        events = []

        @framework.event_bus.on("Product", None)
        async def tracker(event):
            events.append(event)

        # Operations
        product = await framework.create("Product", ProductFactory.build())
        await asyncio.sleep(0.1)

        await framework.update("Product", product.id, {"price": 299.99})
        await asyncio.sleep(0.1)

        await framework.delete("Product", product.id)
        await asyncio.sleep(0.1)

        # Events should match operations
        assert len(events) >= 3

    async def test_bulk_operation_consistency(self, framework):
        """Test bulk operations maintain consistency"""
        framework.register_entity(Product)

        # Bulk create
        products = ProductFactory.build_batch(10)
        response = await framework.bulk_create("Product", products)

        assert response.created == 10

        # Verify all in database
        all_products = await framework.list("Product")
        assert len(all_products) == 10

        # Update all
        for product in all_products:
            await framework.update("Product", product.id, {"price": 99.99})

        # Verify all updated
        updated_products = await framework.list("Product")
        assert all(p.price == 99.99 for p in updated_products)

        # Delete all
        for product in all_products:
            await framework.delete("Product", product.id)

        # Verify all deleted
        final_products = await framework.list("Product")
        assert len(final_products) == 0


@pytest.mark.e2e
@pytest.mark.asyncio
class TestStressRecovery:
    """Test recovery under stress conditions"""

    async def test_high_volume_recovery(self, framework):
        """Test system recovers after high volume operations"""
        framework.register_entity(Product)

        # High volume creates
        for _ in range(50):
            await framework.create("Product", ProductFactory.build())

        # System should still be responsive
        products = await framework.list("Product", limit=100)
        assert len(products) == 50

        # Can still perform operations
        new_product = await framework.create("Product", ProductFactory.build())
        assert new_product.id is not None

    async def test_recovery_from_hook_errors(self, framework):
        """Test system recovers when hooks raise errors"""

        error_count = [0]

        class FlakyHooks(EntityHooks):
            @staticmethod
            def before_create(instance):
                error_count[0] += 1
                if error_count[0] % 3 == 0:
                    raise Exception("Simulated error")
                return instance

        framework.register_entity(Product, hooks=FlakyHooks())

        successful = []
        failed = 0

        # Try creating 10 products
        for i in range(10):
            try:
                product = await framework.create("Product", ProductFactory.build())
                successful.append(product)
            except Exception:
                failed += 1

        # Some should succeed, some should fail
        assert len(successful) > 0
        assert failed > 0

        # System should still be functional
        products = await framework.list("Product")
        assert len(products) == len(successful)

    async def test_cleanup_after_partial_failure(self, framework):
        """Test proper cleanup after partial failures"""
        framework.register_entity(Product)

        initial_count = len(await framework.list("Product"))

        # Create some products
        for _ in range(5):
            await framework.create("Product", ProductFactory.build())

        # Verify they were created
        after_create = len(await framework.list("Product"))
        assert after_create == initial_count + 5

        # Try bulk operation with some failures
        products = ProductFactory.build_batch(10)
        response = await framework.bulk_create("Product", products)

        # Check final state is consistent
        final_count = len(await framework.list("Product"))
        assert final_count == after_create + response.created


@pytest.mark.e2e
@pytest.mark.asyncio
class TestLongTermStability:
    """Test long-term stability"""

    async def test_extended_operation_stability(self, framework):
        """Test stability over extended operations"""
        framework.register_entity(Product)

        # Perform 100 operations
        for i in range(100):
            if i % 3 == 0:
                product = await framework.create("Product", ProductFactory.build())
            elif i % 3 == 1:
                products = await framework.list("Product", limit=1)
                if products:
                    await framework.update(
                        "Product",
                        products[0].id,
                        {"price": float(i)}
                    )
            else:
                products = await framework.list("Product", limit=1)
                if products:
                    await framework.delete("Product", products[0].id)

        # System should still be functional
        final_products = await framework.list("Product")
        assert isinstance(final_products, list)

    async def test_connection_stability(self, framework):
        """Test that connections remain stable over time"""
        framework.register_entity(Product)

        # Perform operations over "time" (simulated with iterations)
        for _ in range(20):
            await framework.create("Product", ProductFactory.build())
            await asyncio.sleep(0.05)

        # Connections should still work
        products = await framework.list("Product")
        assert len(products) == 20

        # Can still perform new operations
        new_product = await framework.create("Product", ProductFactory.build())
        assert new_product.id is not None
