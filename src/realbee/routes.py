"""
Auto-generated route handlers for CRUD operations
"""
from typing import List, Optional, Dict, Any, Type
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from .models import (
    EventType,
    SearchRequest,
    SearchResult,
    PaginationParams,
    BulkCreateResponse
)
from .exceptions import EntityNotFoundException
from .utils import get_entity_name


class RouteGenerator:
    """Generates CRUD routes for entities"""

    def __init__(self, framework):
        """
        Initialize route generator.

        Args:
            framework: Reference to CRUDFramework instance
        """
        self.framework = framework

    def generate_routes(
        self,
        entity_type: Type[BaseModel],
        router: APIRouter
    ):
        """
        Generate all CRUD routes for an entity type.

        Args:
            entity_type: Pydantic model class
            router: FastAPI router to add routes to
        """
        entity_name = get_entity_name(entity_type)
        entity_name_lower = entity_name.lower()
        entity_name_plural = entity_name_lower + "s"

        # CREATE
        @router.post(
            f"/{entity_name_plural}",
            response_model=entity_type,
            status_code=201,
            tags=[entity_name]
        )
        async def create_entity(entity: entity_type):
            """Create a new entity"""
            return await self.framework.create(entity_name, entity)

        # LIST
        @router.get(
            f"/{entity_name_plural}",
            response_model=List[entity_type],
            tags=[entity_name]
        )
        async def list_entities(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
        ):
            """List entities with pagination"""
            return await self.framework.list(entity_name, skip=skip, limit=limit)

        # GET BY ID
        @router.get(
            f"/{entity_name_plural}/{{entity_id}}",
            response_model=entity_type,
            tags=[entity_name]
        )
        async def get_entity(entity_id: int):
            """Get entity by ID"""
            result = await self.framework.get(entity_name, entity_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            return result

        # UPDATE
        @router.patch(
            f"/{entity_name_plural}/{{entity_id}}",
            response_model=entity_type,
            tags=[entity_name]
        )
        async def update_entity(entity_id: int, updates: Dict[str, Any]):
            """Update entity"""
            result = await self.framework.update(entity_name, entity_id, updates)
            if not result:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            return result

        # DELETE
        @router.delete(
            f"/{entity_name_plural}/{{entity_id}}",
            status_code=204,
            tags=[entity_name]
        )
        async def delete_entity(entity_id: int):
            """Delete entity"""
            success = await self.framework.delete(entity_name, entity_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"{entity_name} not found")
            return None

        # BULK CREATE
        @router.post(
            f"/{entity_name_plural}/bulk",
            response_model=BulkCreateResponse,
            status_code=201,
            tags=[entity_name]
        )
        async def bulk_create_entities(entities: List[entity_type]):
            """Bulk create entities"""
            return await self.framework.bulk_create(entity_name, entities)

        # SEARCH (if entity has vector fields)
        metadata = self.framework._metadata.get(entity_name)
        if metadata and metadata.has_search:
            @router.post(
                f"/{entity_name_plural}/search",
                response_model=List[entity_type],
                tags=[entity_name]
            )
            async def search_entities(request: SearchRequest):
                """Multimodal search"""
                return await self.framework.search(entity_name, request)

        # WEBSOCKET
        @router.websocket(f"/ws/{entity_name_plural}")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self.framework.ws_manager.connect(websocket, entity_name)

            try:
                while True:
                    # Receive messages from client
                    data = await websocket.receive_json()
                    await self.framework.ws_manager.handle_client_message(websocket, data)

            except WebSocketDisconnect:
                self.framework.ws_manager.disconnect(websocket, entity_name)
            except Exception as e:
                print(f"WebSocket error: {e}")
                self.framework.ws_manager.disconnect(websocket, entity_name)
