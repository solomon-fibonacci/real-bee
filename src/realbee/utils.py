"""
Utility functions for real-bee framework
"""
import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel


def to_snake_case(text: str) -> str:
    """Convert CamelCase to snake_case"""
    result = []
    for i, char in enumerate(text):
        if char.isupper() and i > 0:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)


def get_table_name(entity_type: Type[BaseModel]) -> str:
    """Generate table name from entity type"""
    return to_snake_case(entity_type.__name__) + 's'


def get_entity_name(entity_type: Type[BaseModel]) -> str:
    """Get entity name from type"""
    return entity_type.__name__


def generate_cache_key(prefix: str, entity_name: str, entity_id: Optional[int] = None) -> str:
    """Generate cache key"""
    if entity_id is not None:
        return f"{prefix}:{entity_name}:{entity_id}"
    return f"{prefix}:{entity_name}"


def generate_event_id(entity_name: str, entity_id: Optional[int], timestamp: datetime) -> str:
    """Generate unique event ID"""
    data = f"{entity_name}:{entity_id}:{timestamp.isoformat()}"
    return hashlib.md5(data.encode()).hexdigest()


def get_vector_fields(entity_type: Type[BaseModel]) -> List[str]:
    """Extract vector fields from entity configuration"""
    if hasattr(entity_type, "Config") and hasattr(entity_type.Config, "vector_fields"):
        return entity_type.Config.vector_fields
    return []


def serialize_for_json(obj: Any) -> Any:
    """Serialize objects for JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    return obj


async def run_in_threadpool(func, *args, **kwargs):
    """Run blocking function in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def validate_vector_field(field_name: str, entity_type: Type[BaseModel]) -> bool:
    """Check if field exists and is valid for vectorization"""
    if field_name not in entity_type.model_fields:
        return False

    field = entity_type.model_fields[field_name]
    # Check if field is string or optional string
    field_type = field.annotation

    # Handle Optional types
    if hasattr(field_type, "__origin__"):
        if field_type.__origin__ is type(None):
            return False
        # For Union types (like Optional), get the non-None type
        args = getattr(field_type, "__args__", ())
        field_type = next((arg for arg in args if arg is not type(None)), None)

    return field_type is str


class AsyncBatch:
    """Helper for batching async operations"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.items = []

    def add(self, item: Any) -> bool:
        """Add item to batch. Returns True if batch is full."""
        self.items.append(item)
        return len(self.items) >= self.max_size

    def get_items(self) -> List[Any]:
        """Get all items and clear batch"""
        items = self.items.copy()
        self.items.clear()
        return items

    def __len__(self) -> int:
        return len(self.items)
