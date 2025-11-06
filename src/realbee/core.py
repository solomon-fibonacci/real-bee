"""
Core configuration and base classes for real-bee framework
"""

from typing import Any
from enum import Enum
from pydantic import BaseModel, Field


class IndexStrategy(str, Enum):
    """FAISS index strategies"""

    FLAT = "IndexFlatIP"  # Exact search, inner product
    IVF_FLAT = "IndexIVFFlat"  # Inverted file with flat quantizer
    IVF_PQ = "IndexIVFPQ"  # Inverted file with product quantization
    HNSW = "IndexHNSWFlat"  # Hierarchical Navigable Small World


class FrameworkConfig(BaseModel):
    """Configuration for CRUDFramework"""

    # Database Configuration
    postgres_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/realbee",
        description="PostgreSQL connection URL",
    )
    postgres_pool_size: int = Field(
        default=20, ge=1, description="Database connection pool size"
    )
    postgres_max_overflow: int = Field(
        default=10, ge=0, description="Max overflow connections"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_pool_size: int = Field(
        default=50, ge=1, description="Redis connection pool size"
    )
    redis_decode_responses: bool = Field(
        default=True, description="Decode Redis responses"
    )

    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=300, ge=0, description="Cache TTL in seconds")
    cache_prefix: str = Field(default="realbee", description="Cache key prefix")

    # FAISS Configuration
    faiss_index_type: IndexStrategy = Field(
        default=IndexStrategy.FLAT, description="FAISS index type"
    )
    faiss_dimension: int = Field(default=512, ge=1, description="Embedding dimension")
    faiss_nprobe: int = Field(
        default=10, ge=1, description="Number of probes for IVF indices"
    )
    faiss_nlist: int = Field(
        default=100, ge=1, description="Number of clusters for IVF indices"
    )

    # CLIP Configuration
    clip_model: str = Field(default="ViT-B/32", description="CLIP model variant")
    clip_device: str = Field(default="cpu", description="Device for CLIP (cpu/cuda)")
    clip_batch_size: int = Field(
        default=32, ge=1, description="Batch size for CLIP encoding"
    )

    # WebSocket Configuration
    ws_heartbeat_interval: int = Field(
        default=30, ge=1, description="WebSocket heartbeat interval (seconds)"
    )
    ws_max_connections: int = Field(
        default=10000, ge=1, description="Maximum WebSocket connections"
    )
    ws_message_queue_size: int = Field(
        default=1000, ge=1, description="WebSocket message queue size"
    )

    # Performance Configuration
    batch_size: int = Field(default=100, ge=1, description="Batch operation size")
    max_concurrent_tasks: int = Field(
        default=50, ge=1, description="Maximum concurrent async tasks"
    )

    # Event Bus Configuration
    event_history_size: int = Field(
        default=1000, ge=0, description="Number of events to keep in history"
    )
    event_ttl: int = Field(default=3600, ge=0, description="Event TTL in seconds")

    class Config:
        use_enum_values = True


class EntityHooks:
    """
    Base class for entity lifecycle hooks.
    Override methods to add custom behavior.
    """

    @staticmethod
    def before_create(instance: Any) -> Any:
        """
        Called before creating an entity.

        Args:
            instance: The entity instance to be created

        Returns:
            Modified entity instance (or raise exception to abort)
        """
        return instance

    @staticmethod
    async def after_create(instance: Any) -> None:
        """
        Called after creating an entity.

        Args:
            instance: The created entity instance
        """
        pass

    @staticmethod
    def before_update(instance: Any, updates: dict) -> dict:
        """
        Called before updating an entity.

        Args:
            instance: The existing entity instance
            updates: Dictionary of fields to update

        Returns:
            Modified updates dictionary (or raise exception to abort)
        """
        return updates

    @staticmethod
    async def after_update(instance: Any) -> None:
        """
        Called after updating an entity.

        Args:
            instance: The updated entity instance
        """
        pass

    @staticmethod
    async def before_delete(instance: Any) -> bool:
        """
        Called before deleting an entity.

        Args:
            instance: The entity instance to be deleted

        Returns:
            True to allow deletion, False to prevent it
        """
        return True

    @staticmethod
    async def after_delete(entity_id: int) -> None:
        """
        Called after deleting an entity.

        Args:
            entity_id: The ID of the deleted entity
        """
        pass


def searchable(*fields: str):
    """
    Decorator to mark fields as searchable (for vector embeddings).

    Usage:
        @searchable("description", "image_url")
        class Product(BaseModel):
            description: str
            image_url: str
    """

    def decorator(cls):
        if not hasattr(cls, "Config"):
            cls.Config = type("Config", (), {})
        cls.Config.vector_fields = list(fields)
        return cls

    return decorator
