"""
Unit tests for data models
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from realbee.models import (
    EventType,
    Event,
    SearchRequest,
    SearchResult,
    PaginationParams,
    BulkCreateResponse,
    WebSocketMessage,
    EntityMetadata,
)


class TestEventType:
    """Tests for EventType enum"""

    def test_event_types_exist(self):
        assert EventType.CREATED == "created"
        assert EventType.UPDATED == "updated"
        assert EventType.DELETED == "deleted"
        assert EventType.BULK_CREATED == "bulk_created"

    def test_event_type_is_string(self):
        assert isinstance(EventType.CREATED.value, str)


class TestEvent:
    """Tests for Event model"""

    def test_create_valid_event(self):
        event = Event(
            id="test-123",
            entity_type="Product",
            entity_id=1,
            event_type=EventType.CREATED,
            data={"name": "Test Product"}
        )
        assert event.id == "test-123"
        assert event.entity_type == "Product"
        assert event.entity_id == 1
        assert event.event_type == EventType.CREATED
        assert event.data == {"name": "Test Product"}

    def test_event_with_timestamp(self):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        event = Event(
            id="test-123",
            entity_type="Product",
            event_type=EventType.CREATED,
            data={},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp

    def test_event_default_timestamp(self):
        event = Event(
            id="test-123",
            entity_type="Product",
            event_type=EventType.CREATED,
            data={}
        )
        assert isinstance(event.timestamp, datetime)

    def test_event_with_metadata(self):
        event = Event(
            id="test-123",
            entity_type="Product",
            event_type=EventType.CREATED,
            data={},
            metadata={"user_id": 123, "ip": "192.168.1.1"}
        )
        assert event.metadata == {"user_id": 123, "ip": "192.168.1.1"}

    def test_event_serialization(self):
        event = Event(
            id="test-123",
            entity_type="Product",
            event_type=EventType.CREATED,
            data={"name": "Test"},
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        data = event.model_dump()
        assert data["id"] == "test-123"
        assert data["event_type"] == "created"

    def test_event_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Event(id="test")  # Missing required fields


class TestSearchRequest:
    """Tests for SearchRequest model"""

    def test_text_only_search(self):
        request = SearchRequest(text="running shoes")
        assert request.text == "running shoes"
        assert request.image_url is None
        assert request.k == 10

    def test_image_only_search(self):
        request = SearchRequest(image_url="https://example.com/image.jpg")
        assert request.image_url == "https://example.com/image.jpg"
        assert request.text is None

    def test_multimodal_search(self):
        request = SearchRequest(
            text="red shoes",
            image_url="https://example.com/shoe.jpg",
            text_weight=0.7,
            k=20
        )
        assert request.text == "red shoes"
        assert request.image_url == "https://example.com/shoe.jpg"
        assert request.text_weight == 0.7
        assert request.k == 20

    def test_default_text_weight(self):
        request = SearchRequest(text="test")
        assert request.text_weight == 0.5

    def test_default_k_value(self):
        request = SearchRequest(text="test")
        assert request.k == 10

    def test_text_weight_validation(self):
        # Valid weights
        SearchRequest(text="test", text_weight=0.0)
        SearchRequest(text="test", text_weight=0.5)
        SearchRequest(text="test", text_weight=1.0)

        # Invalid weights
        with pytest.raises(ValidationError):
            SearchRequest(text="test", text_weight=-0.1)
        with pytest.raises(ValidationError):
            SearchRequest(text="test", text_weight=1.1)

    def test_k_validation(self):
        # Valid k values
        SearchRequest(text="test", k=1)
        SearchRequest(text="test", k=1000)

        # Invalid k values
        with pytest.raises(ValidationError):
            SearchRequest(text="test", k=0)
        with pytest.raises(ValidationError):
            SearchRequest(text="test", k=1001)

    def test_with_filters(self):
        request = SearchRequest(
            text="test",
            filters={"category": "electronics", "price_min": 100}
        )
        assert request.filters == {"category": "electronics", "price_min": 100}


class TestSearchResult:
    """Tests for SearchResult model"""

    def test_create_search_result(self):
        result = SearchResult(
            entity={"id": 1, "name": "Test Product"},
            score=0.95,
            rank=1
        )
        assert result.entity == {"id": 1, "name": "Test Product"}
        assert result.score == 0.95
        assert result.rank == 1

    def test_search_result_validation(self):
        with pytest.raises(ValidationError):
            SearchResult()  # Missing required fields


class TestPaginationParams:
    """Tests for PaginationParams model"""

    def test_default_values(self):
        params = PaginationParams()
        assert params.skip == 0
        assert params.limit == 100

    def test_custom_values(self):
        params = PaginationParams(skip=10, limit=50)
        assert params.skip == 10
        assert params.limit == 50

    def test_skip_validation(self):
        PaginationParams(skip=0)  # Valid
        with pytest.raises(ValidationError):
            PaginationParams(skip=-1)  # Invalid

    def test_limit_validation(self):
        PaginationParams(limit=1)  # Valid min
        PaginationParams(limit=1000)  # Valid max
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)  # Invalid
        with pytest.raises(ValidationError):
            PaginationParams(limit=1001)  # Invalid


class TestBulkCreateResponse:
    """Tests for BulkCreateResponse model"""

    def test_successful_bulk_create(self):
        response = BulkCreateResponse(
            created=3,
            entities=[
                {"id": 1, "name": "Product 1"},
                {"id": 2, "name": "Product 2"},
                {"id": 3, "name": "Product 3"},
            ],
            errors=[]
        )
        assert response.created == 3
        assert len(response.entities) == 3
        assert len(response.errors) == 0

    def test_bulk_create_with_errors(self):
        response = BulkCreateResponse(
            created=2,
            entities=[
                {"id": 1, "name": "Product 1"},
                {"id": 2, "name": "Product 2"},
            ],
            errors=[
                {"entity": {"name": "Bad Product"}, "error": "Validation failed"}
            ]
        )
        assert response.created == 2
        assert len(response.errors) == 1

    def test_default_errors_list(self):
        response = BulkCreateResponse(created=1, entities=[{"id": 1}])
        assert response.errors == []


class TestWebSocketMessage:
    """Tests for WebSocketMessage model"""

    def test_create_message(self):
        msg = WebSocketMessage(type="event", data={"entity": "Product"})
        assert msg.type == "event"
        assert msg.data == {"entity": "Product"}
        assert isinstance(msg.timestamp, datetime)

    def test_ping_message(self):
        msg = WebSocketMessage(type="ping")
        assert msg.type == "ping"
        assert msg.data is None

    def test_pong_message(self):
        msg = WebSocketMessage(type="pong", data={"timestamp": "2024-01-01"})
        assert msg.type == "pong"

    def test_error_message(self):
        msg = WebSocketMessage(type="error", data={"message": "Connection lost"})
        assert msg.type == "error"
        assert msg.data["message"] == "Connection lost"

    def test_custom_timestamp(self):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        msg = WebSocketMessage(type="ping", timestamp=timestamp)
        assert msg.timestamp == timestamp

    def test_message_serialization(self):
        msg = WebSocketMessage(
            type="event",
            data={"test": "value"},
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        data = msg.model_dump()
        assert data["type"] == "event"
        assert data["data"] == {"test": "value"}


class TestEntityMetadata:
    """Tests for EntityMetadata model"""

    def test_create_metadata(self):
        from pydantic import BaseModel

        class TestEntity(BaseModel):
            name: str

        metadata = EntityMetadata(
            entity_name="Product",
            entity_type=TestEntity,
            table_name="products",
            vector_fields=["description"],
            has_search=True
        )
        assert metadata.entity_name == "Product"
        assert metadata.entity_type == TestEntity
        assert metadata.table_name == "products"
        assert metadata.vector_fields == ["description"]
        assert metadata.has_search is True

    def test_metadata_without_search(self):
        from pydantic import BaseModel

        class TestEntity(BaseModel):
            name: str

        metadata = EntityMetadata(
            entity_name="User",
            entity_type=TestEntity,
            table_name="users",
            vector_fields=[],
            has_search=False
        )
        assert metadata.has_search is False
        assert metadata.vector_fields == []

    def test_metadata_with_hooks(self):
        from pydantic import BaseModel
        from realbee.core import EntityHooks

        class TestEntity(BaseModel):
            name: str

        class TestHooks(EntityHooks):
            pass

        hooks = TestHooks()
        metadata = EntityMetadata(
            entity_name="Product",
            entity_type=TestEntity,
            table_name="products",
            vector_fields=[],
            has_search=False,
            hooks=hooks
        )
        assert metadata.hooks is not None
