"""
Core data models for real-bee framework
"""

from typing import Any, Optional, List, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can be emitted"""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    BULK_CREATED = "bulk_created"


class Event(BaseModel):
    """Event model for pub/sub system"""

    id: str = Field(..., description="Unique event ID")
    entity_type: str = Field(..., description="Type of entity (e.g., 'Product')")
    entity_id: Optional[int] = Field(None, description="ID of the entity")
    event_type: EventType = Field(..., description="Type of event")
    data: Dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class SearchRequest(BaseModel):
    """Request model for multimodal search"""

    text: Optional[str] = Field(None, description="Text query for search")
    image_url: Optional[str] = Field(None, description="Image URL for search")
    text_weight: float = Field(
        0.5, ge=0, le=1, description="Weight for text query (0-1)"
    )
    k: int = Field(10, ge=1, le=1000, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "comfortable running shoes",
                "image_url": "https://example.com/shoe.jpg",
                "text_weight": 0.7,
                "k": 10,
            }
        }


class SearchResult(BaseModel):
    """Result model for search operations"""

    entity: Dict[str, Any] = Field(..., description="The matched entity")
    score: float = Field(..., description="Similarity score")
    rank: int = Field(..., description="Rank in results")


class PaginationParams(BaseModel):
    """Pagination parameters"""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of records to return"
    )


class BulkCreateResponse(BaseModel):
    """Response for bulk create operations"""

    created: int = Field(..., description="Number of entities created")
    entities: List[Dict[str, Any]] = Field(..., description="Created entities")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Errors encountered"
    )


class WebSocketMessage(BaseModel):
    """WebSocket message format"""

    type: str = Field(..., description="Message type (event, ping, pong, error)")
    data: Optional[Dict[str, Any]] = Field(None, description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class EntityMetadata(BaseModel):
    """Metadata for registered entities"""

    entity_name: str
    entity_type: type
    table_name: str
    vector_fields: List[str]
    has_search: bool
    hooks: Optional[Any] = None
