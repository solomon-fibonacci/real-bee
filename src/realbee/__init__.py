"""
real-bee: REAL-time Back-End on Events

A high-performance, event-driven framework that automatically generates
CRUD endpoints with real-time capabilities and multimodal search for any Pydantic schema.
"""

__version__ = "0.1.0"
__author__ = "real-bee contributors"

from .core import FrameworkConfig, EntityHooks, IndexStrategy
from .framework import CRUDFramework
from .models import Event, EventType, SearchRequest, SearchResult
from .exceptions import (
    RealBeeException,
    EntityNotFoundException,
    ValidationException,
    SearchException,
    WebSocketException,
)

__all__ = [
    # Core
    "FrameworkConfig",
    "EntityHooks",
    "IndexStrategy",
    "CRUDFramework",
    # Models
    "Event",
    "EventType",
    "SearchRequest",
    "SearchResult",
    # Exceptions
    "RealBeeException",
    "EntityNotFoundException",
    "ValidationException",
    "SearchException",
    "WebSocketException",
]
