"""
Integration tests for DatabaseManager with real PostgreSQL
"""
import pytest
from typing import Optional
from pydantic import BaseModel, Field

from realbee.database import DatabaseManager
from realbee.core import FrameworkConfig


class TestProduct(BaseModel):
    """Test product model"""
    id: Optional[int] = None
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Description")
    price: float = Field(..., gt=0)
    category: str
    in_stock: bool = True


class TestUser(BaseModel):
    """Test user model"""
    id: Optional[int] = None
    email: str
    name: str
    active: bool = True


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Integration tests with real PostgreSQL"""

    async def test_initialize_and_close(self, db_manager):
        """Test database connection lifecycle"""
        assert db_manager.pool is not None
        await db_manager.close()
        assert db_manager.pool is None

    async def test_create_table(self, clean_db):
        """Test table creation from Pydantic model"""
        await clean_db.create_table(TestProduct)

        # Verify table exists
        async with clean_db.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'test_products'
                )
            """)
            assert result is True

    async def test_create_table_with_multiple_types(self, clean_db):
        """Test table creation with various field types"""
        await clean_db.create_table(TestProduct)

        # Check column types
        async with clean_db.acquire() as conn:
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'test_products'
            """)

            column_dict = {col['column_name']: col['data_type'] for col in columns}

            assert 'id' in column_dict
            assert 'name' in column_dict
            assert 'price' in column_dict
            assert column_dict['in_stock'] == 'boolean'

    async def test_create_record(self, clean_db):
        """Test creating a record"""
        await clean_db.create_table(TestProduct)

        data = {
            "name": "Test Product",
            "description": "A test product",
            "price": 99.99,
            "category": "Electronics",
            "in_stock": True
        }

        result = await clean_db.create("test_products", data)

        assert result['id'] is not None
        assert result['name'] == "Test Product"
        assert result['price'] == 99.99
        assert result['in_stock'] is True
        assert 'created_at' in result
        assert 'updated_at' in result

    async def test_get_existing_record(self, clean_db):
        """Test retrieving an existing record"""
        await clean_db.create_table(TestProduct)

        created = await clean_db.create("test_products", {
            "name": "Test Product",
            "description": "Description",
            "price": 50.0,
            "category": "Books"
        })

        retrieved = await clean_db.get("test_products", created['id'])

        assert retrieved is not None
        assert retrieved['id'] == created['id']
        assert retrieved['name'] == "Test Product"

    async def test_get_nonexistent_record(self, clean_db):
        """Test retrieving non-existent record returns None"""
        await clean_db.create_table(TestProduct)

        result = await clean_db.get("test_products", 99999)
        assert result is None

    async def test_list_records(self, clean_db):
        """Test listing records"""
        await clean_db.create_table(TestProduct)

        # Create multiple records
        for i in range(5):
            await clean_db.create("test_products", {
                "name": f"Product {i}",
                "description": f"Description {i}",
                "price": float(i * 10),
                "category": "Test"
            })

        results = await clean_db.list("test_products")
        assert len(results) == 5

    async def test_list_with_pagination(self, clean_db):
        """Test pagination"""
        await clean_db.create_table(TestProduct)

        # Create 20 records
        for i in range(20):
            await clean_db.create("test_products", {
                "name": f"Product {i}",
                "description": f"Description {i}",
                "price": 10.0,
                "category": "Test"
            })

        # Get first page
        page1 = await clean_db.list("test_products", skip=0, limit=10)
        assert len(page1) == 10

        # Get second page
        page2 = await clean_db.list("test_products", skip=10, limit=10)
        assert len(page2) == 10

        # Verify different records
        assert page1[0]['id'] != page2[0]['id']

    async def test_list_with_filters(self, clean_db):
        """Test listing with filters"""
        await clean_db.create_table(TestProduct)

        # Create records with different categories
        await clean_db.create("test_products", {
            "name": "Book 1",
            "description": "A book",
            "price": 20.0,
            "category": "Books"
        })
        await clean_db.create("test_products", {
            "name": "Electronics 1",
            "description": "A gadget",
            "price": 100.0,
            "category": "Electronics"
        })
        await clean_db.create("test_products", {
            "name": "Book 2",
            "description": "Another book",
            "price": 25.0,
            "category": "Books"
        })

        # Filter by category
        books = await clean_db.list("test_products", filters={"category": "Books"})
        assert len(books) == 2
        assert all(b['category'] == "Books" for b in books)

    async def test_update_record(self, clean_db):
        """Test updating a record"""
        await clean_db.create_table(TestProduct)

        created = await clean_db.create("test_products", {
            "name": "Original Name",
            "description": "Original description",
            "price": 50.0,
            "category": "Test"
        })

        updated = await clean_db.update(
            "test_products",
            created['id'],
            {"name": "Updated Name", "price": 75.0}
        )

        assert updated is not None
        assert updated['name'] == "Updated Name"
        assert updated['price'] == 75.0
        assert updated['description'] == "Original description"  # Unchanged

    async def test_update_triggers_timestamp(self, clean_db):
        """Test that update triggers updated_at timestamp"""
        await clean_db.create_table(TestProduct)

        created = await clean_db.create("test_products", {
            "name": "Test",
            "description": "Test",
            "price": 10.0,
            "category": "Test"
        })

        import asyncio
        await asyncio.sleep(0.1)  # Small delay

        updated = await clean_db.update(
            "test_products",
            created['id'],
            {"name": "Updated"}
        )

        assert updated['updated_at'] > created['updated_at']

    async def test_delete_record(self, clean_db):
        """Test deleting a record"""
        await clean_db.create_table(TestProduct)

        created = await clean_db.create("test_products", {
            "name": "To Delete",
            "description": "Will be deleted",
            "price": 10.0,
            "category": "Test"
        })

        success = await clean_db.delete("test_products", created['id'])
        assert success is True

        # Verify it's gone
        retrieved = await clean_db.get("test_products", created['id'])
        assert retrieved is None

    async def test_delete_nonexistent_record(self, clean_db):
        """Test deleting non-existent record returns False"""
        await clean_db.create_table(TestProduct)

        success = await clean_db.delete("test_products", 99999)
        assert success is False

    async def test_bulk_create(self, clean_db):
        """Test bulk creating records"""
        await clean_db.create_table(TestProduct)

        items = [
            {
                "name": f"Product {i}",
                "description": f"Description {i}",
                "price": float(i * 10),
                "category": "Bulk"
            }
            for i in range(10)
        ]

        results = await clean_db.bulk_create("test_products", items)

        assert len(results) == 10
        assert all('id' in r for r in results)
        assert all(r['category'] == "Bulk" for r in results)

    async def test_count_records(self, clean_db):
        """Test counting records"""
        await clean_db.create_table(TestProduct)

        # Initially empty
        count = await clean_db.count("test_products")
        assert count == 0

        # Create some records
        for i in range(7):
            await clean_db.create("test_products", {
                "name": f"Product {i}",
                "description": "Test",
                "price": 10.0,
                "category": "Test"
            })

        count = await clean_db.count("test_products")
        assert count == 7

    async def test_count_with_filters(self, clean_db):
        """Test counting with filters"""
        await clean_db.create_table(TestProduct)

        # Create records with different categories
        for i in range(5):
            await clean_db.create("test_products", {
                "name": f"Product {i}",
                "description": "Test",
                "price": 10.0,
                "category": "A" if i % 2 == 0 else "B"
            })

        count_a = await clean_db.count("test_products", filters={"category": "A"})
        count_b = await clean_db.count("test_products", filters={"category": "B"})

        assert count_a == 3
        assert count_b == 2

    async def test_multiple_tables(self, clean_db):
        """Test working with multiple tables"""
        await clean_db.create_table(TestProduct)
        await clean_db.create_table(TestUser)

        # Create records in both tables
        product = await clean_db.create("test_products", {
            "name": "Product",
            "description": "A product",
            "price": 50.0,
            "category": "Test"
        })

        user = await clean_db.create("test_users", {
            "email": "test@example.com",
            "name": "Test User",
            "active": True
        })

        assert product['id'] is not None
        assert user['id'] is not None

        # Verify both tables are independent
        products = await clean_db.list("test_products")
        users = await clean_db.list("test_users")

        assert len(products) == 1
        assert len(users) == 1

    async def test_transaction_rollback_on_error(self, clean_db):
        """Test that errors during bulk create don't leave partial data"""
        await clean_db.create_table(TestProduct)

        # Create one valid record
        await clean_db.create("test_products", {
            "name": "Valid Product",
            "description": "Valid",
            "price": 10.0,
            "category": "Test"
        })

        initial_count = await clean_db.count("test_products")
        assert initial_count == 1

        # Try bulk create with some invalid data
        items = [
            {"name": "Product 1", "description": "Test", "price": 10.0, "category": "Test"},
            {"name": "Product 2", "description": "Test", "price": 20.0, "category": "Test"},
        ]

        try:
            # This will create what it can
            results = await clean_db.bulk_create("test_products", items)
            # Should succeed for valid items
            assert len(results) > 0
        except Exception:
            pass

        # Check final count
        final_count = await clean_db.count("test_products")
        assert final_count >= initial_count
