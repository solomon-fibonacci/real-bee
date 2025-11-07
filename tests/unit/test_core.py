"""
Unit tests for core configuration and base classes
"""
import pytest
from pydantic import BaseModel

from realbee.core import (
    IndexStrategy,
    FrameworkConfig,
    EntityHooks,
    searchable,
)


class TestIndexStrategy:
    """Tests for IndexStrategy enum"""

    def test_index_strategies_exist(self):
        assert IndexStrategy.FLAT == "IndexFlatIP"
        assert IndexStrategy.IVF_FLAT == "IndexIVFFlat"
        assert IndexStrategy.IVF_PQ == "IndexIVFPQ"
        assert IndexStrategy.HNSW == "IndexHNSWFlat"


class TestFrameworkConfig:
    """Tests for FrameworkConfig"""

    def test_default_config(self):
        config = FrameworkConfig()
        assert config.postgres_url == "postgresql://postgres:postgres@localhost:5432/realbee"
        assert config.postgres_pool_size == 20
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.cache_enabled is True
        assert config.faiss_dimension == 512

    def test_custom_config(self):
        config = FrameworkConfig(
            postgres_url="postgresql://user:pass@db:5432/custom",
            postgres_pool_size=10,
            redis_url="redis://cache:6379/1",
            cache_enabled=False,
        )
        assert config.postgres_url == "postgresql://user:pass@db:5432/custom"
        assert config.postgres_pool_size == 10
        assert config.redis_url == "redis://cache:6379/1"
        assert config.cache_enabled is False

    def test_postgres_config(self):
        config = FrameworkConfig(
            postgres_pool_size=50,
            postgres_max_overflow=20
        )
        assert config.postgres_pool_size == 50
        assert config.postgres_max_overflow == 20

    def test_redis_config(self):
        config = FrameworkConfig(
            redis_pool_size=100,
            redis_decode_responses=False
        )
        assert config.redis_pool_size == 100
        assert config.redis_decode_responses is False

    def test_cache_config(self):
        config = FrameworkConfig(
            cache_ttl=600,
            cache_prefix="myapp"
        )
        assert config.cache_ttl == 600
        assert config.cache_prefix == "myapp"

    def test_faiss_config(self):
        config = FrameworkConfig(
            faiss_index_type=IndexStrategy.IVF_FLAT,
            faiss_dimension=768,
            faiss_nprobe=20,
            faiss_nlist=200
        )
        assert config.faiss_index_type == IndexStrategy.IVF_FLAT
        assert config.faiss_dimension == 768
        assert config.faiss_nprobe == 20
        assert config.faiss_nlist == 200

    def test_clip_config(self):
        config = FrameworkConfig(
            clip_model="ViT-L/14",
            clip_device="cuda",
            clip_batch_size=64
        )
        assert config.clip_model == "ViT-L/14"
        assert config.clip_device == "cuda"
        assert config.clip_batch_size == 64

    def test_websocket_config(self):
        config = FrameworkConfig(
            ws_heartbeat_interval=60,
            ws_max_connections=5000,
            ws_message_queue_size=2000
        )
        assert config.ws_heartbeat_interval == 60
        assert config.ws_max_connections == 5000
        assert config.ws_message_queue_size == 2000

    def test_performance_config(self):
        config = FrameworkConfig(
            batch_size=200,
            max_concurrent_tasks=100
        )
        assert config.batch_size == 200
        assert config.max_concurrent_tasks == 100

    def test_event_config(self):
        config = FrameworkConfig(
            event_history_size=500,
            event_ttl=7200
        )
        assert config.event_history_size == 500
        assert config.event_ttl == 7200


class TestEntityHooks:
    """Tests for EntityHooks base class"""

    def test_before_create_default(self):
        hooks = EntityHooks()
        instance = {"name": "Test"}
        result = hooks.before_create(instance)
        assert result == instance

    @pytest.mark.asyncio
    async def test_after_create_default(self):
        hooks = EntityHooks()
        instance = {"id": 1, "name": "Test"}
        # Should not raise any errors
        await hooks.after_create(instance)

    def test_before_update_default(self):
        hooks = EntityHooks()
        instance = {"id": 1, "name": "Test"}
        updates = {"name": "Updated"}
        result = hooks.before_update(instance, updates)
        assert result == updates

    @pytest.mark.asyncio
    async def test_after_update_default(self):
        hooks = EntityHooks()
        instance = {"id": 1, "name": "Updated"}
        await hooks.after_update(instance)

    @pytest.mark.asyncio
    async def test_before_delete_default(self):
        hooks = EntityHooks()
        instance = {"id": 1, "name": "Test"}
        result = await hooks.before_delete(instance)
        assert result is True

    @pytest.mark.asyncio
    async def test_after_delete_default(self):
        hooks = EntityHooks()
        await hooks.after_delete(1)

    def test_custom_hooks(self):
        """Test creating custom hooks"""

        class CustomHooks(EntityHooks):
            @staticmethod
            def before_create(instance):
                instance["modified"] = True
                return instance

            @staticmethod
            async def after_create(instance):
                # Custom logic here
                pass

        hooks = CustomHooks()
        instance = {"name": "Test"}
        result = hooks.before_create(instance)
        assert result["modified"] is True

    @pytest.mark.asyncio
    async def test_before_delete_can_prevent(self):
        """Test that before_delete can prevent deletion"""

        class CustomHooks(EntityHooks):
            @staticmethod
            async def before_delete(instance):
                # Prevent deletion of certain instances
                if instance.get("protected"):
                    return False
                return True

        hooks = CustomHooks()
        result1 = await hooks.before_delete({"id": 1, "protected": True})
        result2 = await hooks.before_delete({"id": 2, "protected": False})
        assert result1 is False
        assert result2 is True


class TestSearchableDecorator:
    """Tests for @searchable decorator"""

    def test_searchable_single_field(self):
        @searchable("description")
        class Product(BaseModel):
            name: str
            description: str

        assert hasattr(Product, "Config")
        assert hasattr(Product.Config, "vector_fields")
        assert Product.Config.vector_fields == ["description"]

    def test_searchable_multiple_fields(self):
        @searchable("description", "image_url")
        class Product(BaseModel):
            name: str
            description: str
            image_url: str

        assert Product.Config.vector_fields == ["description", "image_url"]

    def test_searchable_no_fields(self):
        @searchable()
        class User(BaseModel):
            name: str

        assert User.Config.vector_fields == []

    def test_searchable_with_existing_config(self):
        """Test that decorator doesn't override existing Config"""

        @searchable("description")
        class Product(BaseModel):
            name: str
            description: str

            class Config:
                some_other_setting = True

        # Should add vector_fields without removing other settings
        assert hasattr(Product.Config, "vector_fields")
        assert hasattr(Product.Config, "some_other_setting")

    def test_searchable_creates_list(self):
        @searchable("field1", "field2")
        class TestModel(BaseModel):
            field1: str
            field2: str

        # Should create a list, not tuple
        assert isinstance(TestModel.Config.vector_fields, list)
        assert len(TestModel.Config.vector_fields) == 2
