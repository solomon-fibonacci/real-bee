"""
Unit tests for DatabaseManager (using mocks)
"""
import pytest
from typing import Optional
from pydantic import BaseModel

from realbee.database import DatabaseManager
from realbee.core import FrameworkConfig
from realbee.exceptions import DatabaseException
from tests.mocks import MockDatabase


class TestProduct(BaseModel):
    """Test product model"""
    id: Optional[int] = None
    name: str
    price: float


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization"""

    def test_init_with_config(self):
        config = FrameworkConfig(postgres_url="postgresql://test:test@localhost:5432/test")
        db = DatabaseManager(config)
        assert db.config == config
        assert db.pool is None

    def test_init_with_custom_pool_size(self):
        config = FrameworkConfig(postgres_pool_size=50)
        db = DatabaseManager(config)
        assert db.config.postgres_pool_size == 50


class TestGetPgType:
    """Tests for _get_pg_type method"""

    def test_int_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(int) == "INTEGER"

    def test_float_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(float) == "DOUBLE PRECISION"

    def test_str_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(str) == "TEXT"

    def test_bool_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(bool) == "BOOLEAN"

    def test_dict_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(dict) == "JSONB"

    def test_list_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._get_pg_type(list) == "JSONB"

    def test_optional_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        # For Optional[int], should return INTEGER
        from typing import Optional
        assert db._get_pg_type(Optional[int]) == "INTEGER"

    def test_unknown_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        # Unknown types should default to TEXT
        class CustomType:
            pass
        assert db._get_pg_type(CustomType) == "TEXT"


class TestIsOptional:
    """Tests for _is_optional method"""

    def test_optional_type(self):
        from typing import Optional
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._is_optional(Optional[str]) is True

    def test_non_optional_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._is_optional(str) is False

    def test_none_type(self):
        config = FrameworkConfig()
        db = DatabaseManager(config)
        assert db._is_optional(type(None)) is False


@pytest.mark.asyncio
class TestMockDatabaseOperations:
    """Tests using mock database"""

    async def test_create_operation(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        data = {"name": "Test Product", "price": 99.99}
        result = await mock_db.create("products", data)

        assert result["id"] == 1
        assert result["name"] == "Test Product"
        assert result["price"] == 99.99

    async def test_get_existing_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        # Create first
        created = await mock_db.create("products", {"name": "Test", "price": 50.0})

        # Then get
        result = await mock_db.get("products", created["id"])
        assert result is not None
        assert result["name"] == "Test"

    async def test_get_nonexistent_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        result = await mock_db.get("products", 999)
        assert result is None

    async def test_list_empty(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        result = await mock_db.list("products")
        assert result == []

    async def test_list_with_items(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        # Create some items
        await mock_db.create("products", {"name": "Product 1", "price": 10.0})
        await mock_db.create("products", {"name": "Product 2", "price": 20.0})
        await mock_db.create("products", {"name": "Product 3", "price": 30.0})

        result = await mock_db.list("products")
        assert len(result) == 3

    async def test_list_with_pagination(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        # Create 10 items
        for i in range(10):
            await mock_db.create("products", {"name": f"Product {i}", "price": float(i)})

        # Get first 5
        result = await mock_db.list("products", skip=0, limit=5)
        assert len(result) == 5

        # Get next 5
        result = await mock_db.list("products", skip=5, limit=5)
        assert len(result) == 5

    async def test_list_with_filters(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        await mock_db.create("products", {"name": "Product 1", "category": "A"})
        await mock_db.create("products", {"name": "Product 2", "category": "B"})
        await mock_db.create("products", {"name": "Product 3", "category": "A"})

        result = await mock_db.list("products", filters={"category": "A"})
        assert len(result) == 2

    async def test_update_existing_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        created = await mock_db.create("products", {"name": "Original", "price": 100.0})
        entity_id = created["id"]

        result = await mock_db.update("products", entity_id, {"name": "Updated"})
        assert result is not None
        assert result["name"] == "Updated"
        assert result["price"] == 100.0  # Unchanged

    async def test_update_nonexistent_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        result = await mock_db.update("products", 999, {"name": "Updated"})
        assert result is None

    async def test_delete_existing_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        created = await mock_db.create("products", {"name": "Test", "price": 50.0})
        entity_id = created["id"]

        success = await mock_db.delete("products", entity_id)
        assert success is True

        # Verify it's gone
        result = await mock_db.get("products", entity_id)
        assert result is None

    async def test_delete_nonexistent_entity(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        success = await mock_db.delete("products", 999)
        assert success is False

    async def test_bulk_create(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        items = [
            {"name": "Product 1", "price": 10.0},
            {"name": "Product 2", "price": 20.0},
            {"name": "Product 3", "price": 30.0},
        ]

        results = await mock_db.bulk_create("products", items)
        assert len(results) == 3
        assert all("id" in r for r in results)

    async def test_count_empty_table(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        count = await mock_db.count("products")
        assert count == 0

    async def test_count_with_items(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        await mock_db.create("products", {"name": "Test 1"})
        await mock_db.create("products", {"name": "Test 2"})
        await mock_db.create("products", {"name": "Test 3"})

        count = await mock_db.count("products")
        assert count == 3

    async def test_count_with_filters(self):
        mock_db = MockDatabase()
        await mock_db.initialize()

        await mock_db.create("products", {"name": "Test 1", "category": "A"})
        await mock_db.create("products", {"name": "Test 2", "category": "B"})
        await mock_db.create("products", {"name": "Test 3", "category": "A"})

        count = await mock_db.count("products", filters={"category": "A"})
        assert count == 2
