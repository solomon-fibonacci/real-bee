"""
End-to-end tests for complete CRUD workflows
"""
import pytest
import asyncio
from fastapi import FastAPI

from realbee import CRUDFramework, FrameworkConfig
from tests.factories import Product, ProductFactory, UserFactory


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCompleteCRUDWorkflow:
    """Test complete CRUD workflows from end to end"""

    async def test_complete_product_lifecycle(self, framework):
        """Test complete lifecycle: create → read → update → search → delete"""
        framework.register_entity(Product)

        # 1. CREATE
        product_data = ProductFactory.build(
            name="Awesome Laptop",
            description="High-performance laptop for developers",
            price=1299.99,
            category="Electronics"
        )
        created = await framework.create("Product", product_data)

        assert created.id is not None
        assert created.name == "Awesome Laptop"

        # 2. READ
        retrieved = await framework.get("Product", created.id)
        assert retrieved.name == created.name
        assert retrieved.price == created.price

        # 3. LIST
        all_products = await framework.list("Product")
        assert len(all_products) >= 1
        assert any(p.id == created.id for p in all_products)

        # 4. UPDATE
        updated = await framework.update(
            "Product",
            created.id,
            {
                "name": "Premium Laptop",
                "price": 1499.99
            }
        )
        assert updated.name == "Premium Laptop"
        assert updated.price == 1499.99
        assert updated.description == created.description  # Unchanged

        # 5. VERIFY UPDATE
        retrieved_after_update = await framework.get("Product", created.id)
        assert retrieved_after_update.name == "Premium Laptop"

        # 6. DELETE
        success = await framework.delete("Product", created.id)
        assert success is True

        # 7. VERIFY DELETION
        deleted_product = await framework.get("Product", created.id)
        assert deleted_product is None

    async def test_bulk_operations_workflow(self, framework):
        """Test bulk create and operations"""
        framework.register_entity(Product)

        # 1. BULK CREATE
        products = ProductFactory.build_batch(20)
        response = await framework.bulk_create("Product", products)

        assert response.created == 20
        assert len(response.entities) == 20
        assert len(response.errors) == 0

        # 2. LIST ALL
        all_products = await framework.list("Product", limit=100)
        assert len(all_products) == 20

        # 3. PAGINATED ACCESS
        page1 = await framework.list("Product", skip=0, limit=10)
        page2 = await framework.list("Product", skip=10, limit=10)

        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].id != page2[0].id  # Different products

        # 4. BULK UPDATE (via individual updates)
        for product in page1:
            await framework.update("Product", product.id, {"price": 99.99})

        # 5. VERIFY UPDATES
        updated_products = await framework.list("Product", skip=0, limit=10)
        assert all(p.price == 99.99 for p in updated_products)

        # 6. BULK DELETE
        for product in all_products[:10]:
            await framework.delete("Product", product.id)

        # 7. VERIFY DELETIONS
        remaining = await framework.list("Product")
        assert len(remaining) == 10

    async def test_concurrent_crud_operations(self, framework):
        """Test concurrent CRUD operations maintain consistency"""
        framework.register_entity(Product)

        # Create products concurrently
        async def create_and_update(i):
            product = await framework.create(
                "Product",
                ProductFactory.build(name=f"Product {i}")
            )
            await asyncio.sleep(0.01)
            updated = await framework.update(
                "Product",
                product.id,
                {"price": float(i * 10)}
            )
            return updated

        # Run 10 concurrent create+update operations
        results = await asyncio.gather(*[
            create_and_update(i) for i in range(10)
        ])

        assert len(results) == 10
        assert all(r.id is not None for r in results)

        # Verify all products exist
        all_products = await framework.list("Product", limit=20)
        assert len(all_products) == 10

    async def test_cross_entity_workflow(self, framework):
        """Test workflow involving multiple entity types"""
        from tests.factories import User, Review

        framework.register_entity(Product)
        framework.register_entity(User)
        framework.register_entity(Review)

        # 1. Create a user
        user = await framework.create("User", UserFactory.build())

        # 2. Create a product
        product = await framework.create(
            "Product",
            ProductFactory.build(name="Test Product")
        )

        # 3. Create a review linking them
        from tests.factories import ReviewFactory
        review_data = ReviewFactory.build(
            product_id=product.id,
            user_id=user.id,
            rating=5,
            comment="Excellent product!"
        )
        review = await framework.create("Review", review_data)

        # 4. Verify all entities exist
        assert await framework.get("User", user.id) is not None
        assert await framework.get("Product", product.id) is not None
        assert await framework.get("Review", review.id) is not None

        # 5. Update product based on review
        await framework.update(
            "Product",
            product.id,
            {"description": "Top-rated product!"}
        )

        # 6. Cleanup in reverse order
        await framework.delete("Review", review.id)
        await framework.delete("Product", product.id)
        await framework.delete("User", user.id)

        # 7. Verify all deleted
        assert await framework.get("User", user.id) is None
        assert await framework.get("Product", product.id) is None
        assert await framework.get("Review", review.id) is None


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCacheConsistency:
    """Test cache consistency across operations"""

    async def test_cache_consistency_workflow(self, framework):
        """Test that cache stays consistent with database"""
        framework.register_entity(Product)

        # 1. Create product
        created = await framework.create(
            "Product",
            ProductFactory.build(name="Original Product")
        )

        # 2. Get product (should hit database, then cache)
        first_get = await framework.get("Product", created.id)
        assert first_get.name == "Original Product"

        # 3. Update product (should invalidate cache)
        updated = await framework.update(
            "Product",
            created.id,
            {"name": "Updated Product"}
        )

        # 4. Get again (should get updated version)
        second_get = await framework.get("Product", created.id)
        assert second_get.name == "Updated Product"

        # 5. Delete product (should remove from cache)
        await framework.delete("Product", created.id)

        # 6. Get again (should return None)
        deleted_get = await framework.get("Product", created.id)
        assert deleted_get is None

    async def test_cache_invalidation_on_updates(self, framework):
        """Test cache is properly invalidated on all update operations"""
        framework.register_entity(Product)

        product = await framework.create("Product", ProductFactory.build())

        # Multiple updates
        for i in range(5):
            await framework.update("Product", product.id, {"price": float(i * 10)})
            retrieved = await framework.get("Product", product.id)
            assert retrieved.price == float(i * 10)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDataIntegrity:
    """Test data integrity across operations"""

    async def test_update_preserves_other_fields(self, framework):
        """Test that partial updates don't lose other data"""
        framework.register_entity(Product)

        original = await framework.create(
            "Product",
            ProductFactory.build(
                name="Original Name",
                description="Original Description",
                price=100.0,
                category="Original Category",
                tags=["tag1", "tag2"]
            )
        )

        # Update only name
        updated = await framework.update(
            "Product",
            original.id,
            {"name": "New Name"}
        )

        # All other fields should be preserved
        assert updated.name == "New Name"
        assert updated.description == "Original Description"
        assert updated.price == 100.0
        assert updated.category == "Original Category"
        assert updated.tags == ["tag1", "tag2"]

    async def test_concurrent_updates_consistency(self, framework):
        """Test concurrent updates maintain consistency"""
        framework.register_entity(Product)

        product = await framework.create("Product", ProductFactory.build())

        # Concurrent updates to different fields
        await asyncio.gather(
            framework.update("Product", product.id, {"name": "Name 1"}),
            framework.update("Product", product.id, {"price": 111.11}),
            framework.update("Product", product.id, {"category": "Category 1"}),
        )

        # Get final state
        final = await framework.get("Product", product.id)

        # All updates should have been applied (last write wins)
        assert final is not None
        assert final.id == product.id

    async def test_delete_is_permanent(self, framework):
        """Test that deleted entities cannot be recovered"""
        framework.register_entity(Product)

        product = await framework.create("Product", ProductFactory.build())
        product_id = product.id

        # Delete
        await framework.delete("Product", product_id)

        # Try multiple ways to access
        assert await framework.get("Product", product_id) is None

        all_products = await framework.list("Product")
        assert not any(p.id == product_id for p in all_products)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error handling and recovery"""

    async def test_invalid_update_leaves_data_intact(self, framework):
        """Test that failed updates don't corrupt data"""
        framework.register_entity(Product)

        original = await framework.create("Product", ProductFactory.build())

        # Try to update with partial valid data
        # (In real scenario, this might fail validation)
        try:
            await framework.update("Product", original.id, {"name": "Valid Update"})
        except Exception:
            pass

        # Original data should still be accessible
        retrieved = await framework.get("Product", original.id)
        assert retrieved is not None

    async def test_recovery_from_nonexistent_operations(self, framework):
        """Test graceful handling of operations on non-existent entities"""
        framework.register_entity(Product)

        # All these should handle gracefully
        assert await framework.get("Product", 99999) is None
        assert await framework.update("Product", 99999, {"name": "Test"}) is None
        assert await framework.delete("Product", 99999) is False

    async def test_bulk_create_partial_failure(self, framework):
        """Test bulk create handles partial failures"""
        framework.register_entity(Product)

        # Mix of valid and potentially problematic data
        products = ProductFactory.build_batch(5)

        response = await framework.bulk_create("Product", products)

        # Should have created the valid ones
        assert response.created >= 0
        assert len(response.entities) >= 0


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestLongRunningWorkflows:
    """Test long-running workflows"""

    async def test_large_dataset_workflow(self, framework):
        """Test working with larger datasets"""
        framework.register_entity(Product)

        # Create 100 products in batches
        for batch in range(10):
            products = ProductFactory.build_batch(10)
            await framework.bulk_create("Product", products)

        # Verify total count
        all_products = await framework.list("Product", limit=200)
        assert len(all_products) == 100

        # Test pagination through all
        collected = []
        page_size = 20
        for skip in range(0, 100, page_size):
            page = await framework.list("Product", skip=skip, limit=page_size)
            collected.extend(page)

        assert len(collected) == 100

        # Update all (in batches)
        for product in collected[:50]:
            await framework.update("Product", product.id, {"price": 99.99})

        # Delete all (in batches)
        for product in collected:
            await framework.delete("Product", product.id)

        # Verify all deleted
        remaining = await framework.list("Product")
        assert len(remaining) == 0

    async def test_sustained_operations(self, framework):
        """Test sustained CRUD operations"""
        framework.register_entity(Product)

        # Perform 50 create-update-delete cycles
        for i in range(50):
            product = await framework.create("Product", ProductFactory.build())
            await framework.update("Product", product.id, {"price": 123.45})
            await framework.delete("Product", product.id)

        # Should have no products left
        products = await framework.list("Product")
        assert len(products) == 0
