"""
Main CRUDFramework class - the heart of real-bee
"""

import asyncio
from typing import Type, Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

from .core import FrameworkConfig, EntityHooks
from .database import DatabaseManager
from .cache import CacheManager
from .events import EventBus
from .search import SearchEngine
from .websocket import WebSocketManager
from .routes import RouteGenerator
from .models import EventType, SearchRequest, BulkCreateResponse, EntityMetadata
from .exceptions import EntityNotFoundException, ValidationException
from .utils import (
    get_entity_name,
    get_table_name,
    get_vector_fields,
    generate_cache_key,
)


class CRUDFramework:
    """
    Main framework class that ties everything together.

    Usage:
        app = FastAPI()
        config = FrameworkConfig(...)
        framework = CRUDFramework(app, config)
        framework.register_entity(Product, hooks=ProductHooks())
    """

    def __init__(self, app: FastAPI, config: FrameworkConfig):
        """
        Initialize the CRUD framework.

        Args:
            app: FastAPI application instance
            config: Framework configuration
        """
        self.app = app
        self.config = config

        # Initialize managers
        self.db = DatabaseManager(config)
        self.cache = CacheManager(config)
        self.search_engine = SearchEngine(config)
        self.ws_manager = WebSocketManager(
            heartbeat_interval=config.ws_heartbeat_interval,
            max_connections=config.ws_max_connections,
        )
        self.event_bus = EventBus(
            self.cache, event_history_size=config.event_history_size
        )
        self.route_generator = RouteGenerator(self)

        # Track registered entities
        self._metadata: Dict[str, EntityMetadata] = {}

        # Setup lifespan events
        self._setup_lifespan()

    def _setup_lifespan(self):
        """Setup application lifespan events"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()

        # Replace the app's lifespan
        self.app.router.lifespan_context = lifespan

    async def startup(self):
        """Initialize all services on startup"""
        print("🐝 Starting real-bee framework...")

        # Initialize database
        await self.db.initialize()
        print("✓ Database connected")

        # Initialize cache/Redis
        await self.cache.initialize()
        print("✓ Redis connected")

        # Initialize search engine
        await self.search_engine.initialize()
        print("✓ Search engine initialized")

        # Start event bus
        await self.event_bus.start()
        print("✓ Event bus started")

        print("🐝 real-bee is ready!")

    async def shutdown(self):
        """Cleanup on shutdown"""
        print("🐝 Shutting down real-bee...")

        # Stop event bus
        await self.event_bus.stop()

        # Close WebSocket connections
        await self.ws_manager.close_all()

        # Close database
        await self.db.close()

        # Close cache
        await self.cache.close()

        # Close search engine
        await self.search_engine.close()

        print("🐝 real-bee stopped")

    def register_entity(
        self,
        entity_type: Type[BaseModel],
        hooks: Optional[EntityHooks] = None,
        router: Optional[APIRouter] = None,
    ):
        """
        Register an entity type and auto-generate CRUD endpoints.

        Args:
            entity_type: Pydantic model class
            hooks: Optional lifecycle hooks
            router: Optional custom router (creates new one if not provided)
        """
        entity_name = get_entity_name(entity_type)
        table_name = get_table_name(entity_type)
        vector_fields = get_vector_fields(entity_type)

        print(f"📝 Registering entity: {entity_name}")

        # Store metadata
        self.metadata[entity_name] = EntityMetadata(
            entity_name=entity_name,
            entity_type=entity_type,
            table_name=table_name,
            vector_fields=vector_fields,
            has_search=len(vector_fields) > 0,
            hooks=hooks or EntityHooks(),
        )

        # Create database table
        asyncio.create_task(self.db.create_table(entity_type))

        # Create search index if needed
        if vector_fields:
            self.search_engine.create_index(entity_name)

        # Generate routes
        if router is None:
            router = APIRouter()

        self.route_generator.generate_routes(entity_type, router)

        # Include router in app
        self.app.include_router(router)

        # Subscribe event bus to WebSocket broadcasts
        async def broadcast_event(event):
            await self.ws_manager.broadcast_event(event)

        self.event_bus.subscribe(entity_name, None, broadcast_event)

        print(f"✓ {entity_name} registered")

    async def create(self, entity_name: str, entity: BaseModel) -> BaseModel:
        """
        Create a new entity.

        Args:
            entity_name: Name of the entity type
            entity: Entity instance to create

        Returns:
            Created entity with ID
        """
        metadata = self._get_metadata(entity_name)
        hooks = metadata.hooks

        # Before create hook
        entity = hooks.before_create(entity)

        # Convert to dict
        data = entity.model_dump()

        # Insert to database
        result = await self.db.create(metadata.table_name, data)

        # Convert back to entity
        created_entity = metadata.entity_type(**result)

        # Add to search index
        if metadata.has_search:
            text_fields = [
                getattr(created_entity, field)
                for field in metadata.vector_fields
                if not field.endswith("_url")
            ]
            image_fields = [
                getattr(created_entity, field)
                for field in metadata.vector_fields
                if field.endswith("_url")
            ]
            asyncio.create_task(
                self.search_engine.add_to_index(
                    entity_name, result["id"], text_fields, image_fields
                )
            )

        # Cache
        cache_key = generate_cache_key(
            self.config.cache_prefix, entity_name, result["id"]
        )
        await self.cache.set(cache_key, result)

        # Emit event
        await self.event_bus.emit(entity_name, EventType.CREATED, result, result["id"])

        # After create hook
        await hooks.after_create(created_entity)

        return created_entity

    async def get(self, entity_name: str, entity_id: int) -> Optional[BaseModel]:
        """
        Get entity by ID.

        Args:
            entity_name: Name of the entity type
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        metadata = self._get_metadata(entity_name)

        # Try cache first
        cache_key = generate_cache_key(self.config.cache_prefix, entity_name, entity_id)
        cached = await self.cache.get(cache_key)
        if cached:
            return metadata.entity_type(**cached)

        # Get from database
        result = await self.db.get(metadata.table_name, entity_id)
        if not result:
            return None

        # Cache it
        await self.cache.set(cache_key, result)

        return metadata.entity_type(**result)

    async def list(
        self,
        entity_name: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[BaseModel]:
        """
        List entities with pagination.

        Args:
            entity_name: Name of the entity type
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters

        Returns:
            List of entity instances
        """
        metadata = self._get_metadata(entity_name)

        results = await self.db.list(
            metadata.table_name, skip=skip, limit=limit, filters=filters
        )

        return [metadata.entity_type(**r) for r in results]

    async def update(
        self, entity_name: str, entity_id: int, updates: Dict[str, Any]
    ) -> Optional[BaseModel]:
        """
        Update an entity.

        Args:
            entity_name: Name of the entity type
            entity_id: Entity ID
            updates: Dictionary of fields to update

        Returns:
            Updated entity or None if not found
        """
        metadata = self._get_metadata(entity_name)
        hooks = metadata.hooks

        # Get existing entity
        existing = await self.get(entity_name, entity_id)
        if not existing:
            return None

        # Before update hook
        updates = hooks.before_update(existing, updates)

        # Update in database
        result = await self.db.update(metadata.table_name, entity_id, updates)
        if not result:
            return None

        updated_entity = metadata.entity_type(**result)

        # Update search index
        if metadata.has_search:
            text_fields = [
                getattr(updated_entity, field)
                for field in metadata.vector_fields
                if not field.endswith("_url")
            ]
            image_fields = [
                getattr(updated_entity, field)
                for field in metadata.vector_fields
                if field.endswith("_url")
            ]
            asyncio.create_task(
                self.search_engine.update_in_index(
                    entity_name, entity_id, text_fields, image_fields
                )
            )

        # Invalidate cache
        cache_key = generate_cache_key(self.config.cache_prefix, entity_name, entity_id)
        await self.cache.delete(cache_key)

        # Emit event
        await self.event_bus.emit(entity_name, EventType.UPDATED, result, entity_id)

        # After update hook
        await hooks.after_update(updated_entity)

        return updated_entity

    async def delete(self, entity_name: str, entity_id: int) -> bool:
        """
        Delete an entity.

        Args:
            entity_name: Name of the entity type
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        metadata = self._get_metadata(entity_name)
        hooks = metadata.hooks

        # Get existing entity
        existing = await self.get(entity_name, entity_id)
        if not existing:
            return False

        # Before delete hook
        allowed = await hooks.before_delete(existing)
        if not allowed:
            raise ValidationException("Delete operation not allowed")

        # Delete from database
        success = await self.db.delete(metadata.table_name, entity_id)
        if not success:
            return False

        # Remove from search index
        if metadata.has_search:
            asyncio.create_task(
                self.search_engine.remove_from_index(entity_name, entity_id)
            )

        # Invalidate cache
        cache_key = generate_cache_key(self.config.cache_prefix, entity_name, entity_id)
        await self.cache.delete(cache_key)

        # Emit event
        await self.event_bus.emit(
            entity_name, EventType.DELETED, {"id": entity_id}, entity_id
        )

        # After delete hook
        await hooks.after_delete(entity_id)

        return True

    async def bulk_create(
        self, entity_name: str, entities: List[BaseModel]
    ) -> BulkCreateResponse:
        """
        Bulk create entities.

        Args:
            entity_name: Name of the entity type
            entities: List of entities to create

        Returns:
            Bulk create response with results and errors
        """
        created = []
        errors = []

        for entity in entities:
            try:
                result = await self.create(entity_name, entity)
                created.append(result.model_dump())
            except Exception as e:
                errors.append({"entity": entity.model_dump(), "error": str(e)})

        # Emit bulk created event
        if created:
            await self.event_bus.emit(
                entity_name, EventType.BULK_CREATED, {"count": len(created)}, None
            )

        return BulkCreateResponse(created=len(created), entities=created, errors=errors)

    async def search(self, entity_name: str, request: SearchRequest) -> List[BaseModel]:
        """
        Perform multimodal search.

        Args:
            entity_name: Name of the entity type
            request: Search request

        Returns:
            List of matching entities
        """
        metadata = self._get_metadata(entity_name)

        if not metadata.has_search:
            raise ValidationException(f"{entity_name} does not support search")

        # Perform search
        results = await self.search_engine.search(entity_name, request)

        # Fetch full entities
        entities = []
        for result in results:
            entity_id = result.entity["id"]
            entity = await self.get(entity_name, entity_id)
            if entity:
                entities.append(entity)

        return entities

    def _get_metadata(self, entity_name: str) -> EntityMetadata:
        """Get metadata for entity or raise exception"""
        if entity_name not in self._metadata:
            raise EntityNotFoundException(f"Entity {entity_name} not registered")
        return self._metadata[entity_name]

    @property
    def metadata(self) -> Dict[str, EntityMetadata]:
        """Access to entity metadata"""
        return self._metadata
