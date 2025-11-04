"""
Unit tests for utility functions
"""
import pytest
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from realbee.utils import (
    to_snake_case,
    get_table_name,
    get_entity_name,
    generate_cache_key,
    generate_event_id,
    get_vector_fields,
    serialize_for_json,
    merge_dicts,
    validate_vector_field,
    AsyncBatch,
)


class TestToSnakeCase:
    """Tests for to_snake_case function"""

    def test_simple_camel_case(self):
        assert to_snake_case("Product") == "product"

    def test_multi_word_camel_case(self):
        assert to_snake_case("ProductReview") == "product_review"

    def test_already_lowercase(self):
        assert to_snake_case("product") == "product"

    def test_all_uppercase(self):
        assert to_snake_case("API") == "a_p_i"

    def test_mixed_case(self):
        assert to_snake_case("HTTPResponse") == "h_t_t_p_response"

    def test_single_letter(self):
        assert to_snake_case("X") == "x"

    def test_empty_string(self):
        assert to_snake_case("") == ""


class TestGetTableName:
    """Tests for get_table_name function"""

    def test_simple_entity(self):
        class Product(BaseModel):
            pass

        assert get_table_name(Product) == "products"

    def test_multi_word_entity(self):
        class ProductReview(BaseModel):
            pass

        assert get_table_name(ProductReview) == "product_reviews"

    def test_already_plural_looking(self):
        class User(BaseModel):
            pass

        assert get_table_name(User) == "users"


class TestGetEntityName:
    """Tests for get_entity_name function"""

    def test_simple_entity(self):
        class Product(BaseModel):
            pass

        assert get_entity_name(Product) == "Product"

    def test_multi_word_entity(self):
        class ProductReview(BaseModel):
            pass

        assert get_entity_name(ProductReview) == "ProductReview"


class TestGenerateCacheKey:
    """Tests for generate_cache_key function"""

    def test_with_entity_id(self):
        key = generate_cache_key("realbee", "Product", 123)
        assert key == "realbee:Product:123"

    def test_without_entity_id(self):
        key = generate_cache_key("realbee", "Product", None)
        assert key == "realbee:Product"

    def test_different_prefix(self):
        key = generate_cache_key("test", "User", 456)
        assert key == "test:User:456"

    def test_zero_entity_id(self):
        key = generate_cache_key("realbee", "Product", 0)
        assert key == "realbee:Product:0"


class TestGenerateEventId:
    """Tests for generate_event_id function"""

    def test_generates_consistent_id(self):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        id1 = generate_event_id("Product", 123, timestamp)
        id2 = generate_event_id("Product", 123, timestamp)
        assert id1 == id2

    def test_different_entities_different_ids(self):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        id1 = generate_event_id("Product", 123, timestamp)
        id2 = generate_event_id("User", 123, timestamp)
        assert id1 != id2

    def test_different_timestamps_different_ids(self):
        id1 = generate_event_id("Product", 123, datetime(2024, 1, 1))
        id2 = generate_event_id("Product", 123, datetime(2024, 1, 2))
        assert id1 != id2

    def test_none_entity_id(self):
        timestamp = datetime(2024, 1, 1)
        id1 = generate_event_id("Product", None, timestamp)
        assert isinstance(id1, str)
        assert len(id1) == 32  # MD5 hash


class TestGetVectorFields:
    """Tests for get_vector_fields function"""

    def test_entity_with_vector_fields(self):
        class Product(BaseModel):
            name: str
            description: str

            class Config:
                vector_fields = ["description"]

        fields = get_vector_fields(Product)
        assert fields == ["description"]

    def test_entity_without_vector_fields(self):
        class User(BaseModel):
            name: str

        fields = get_vector_fields(User)
        assert fields == []

    def test_entity_with_multiple_vector_fields(self):
        class Product(BaseModel):
            name: str
            description: str
            image_url: str

            class Config:
                vector_fields = ["description", "image_url"]

        fields = get_vector_fields(Product)
        assert fields == ["description", "image_url"]


class TestSerializeForJson:
    """Tests for serialize_for_json function"""

    def test_datetime_serialization(self):
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = serialize_for_json(dt)
        assert result == dt.isoformat()

    def test_pydantic_model_serialization(self):
        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        result = serialize_for_json(model)
        assert result == {"name": "test", "value": 42}

    def test_dict_with_datetime(self):
        data = {
            "timestamp": datetime(2024, 1, 1),
            "value": 42
        }
        result = serialize_for_json(data)
        assert isinstance(result["timestamp"], str)
        assert result["value"] == 42

    def test_list_serialization(self):
        data = [1, 2, datetime(2024, 1, 1)]
        result = serialize_for_json(data)
        assert result[0] == 1
        assert result[1] == 2
        assert isinstance(result[2], str)

    def test_nested_structures(self):
        data = {
            "items": [
                {"timestamp": datetime(2024, 1, 1)},
                {"timestamp": datetime(2024, 1, 2)}
            ]
        }
        result = serialize_for_json(data)
        assert isinstance(result["items"][0]["timestamp"], str)

    def test_primitive_types(self):
        assert serialize_for_json(42) == 42
        assert serialize_for_json("test") == "test"
        assert serialize_for_json(True) is True
        assert serialize_for_json(None) is None


class TestMergeDicts:
    """Tests for merge_dicts function"""

    def test_simple_merge(self):
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3}
        result = merge_dicts(dict1, dict2)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_override_values(self):
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = merge_dicts(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_dict_merge(self):
        dict1 = {"a": {"x": 1, "y": 2}}
        dict2 = {"a": {"y": 3, "z": 4}}
        result = merge_dicts(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_empty_dicts(self):
        assert merge_dicts({}, {}) == {}
        assert merge_dicts({"a": 1}, {}) == {"a": 1}
        assert merge_dicts({}, {"a": 1}) == {"a": 1}

    def test_original_dicts_unchanged(self):
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        merge_dicts(dict1, dict2)
        assert dict1 == {"a": 1}
        assert dict2 == {"b": 2}


class TestValidateVectorField:
    """Tests for validate_vector_field function"""

    def test_valid_string_field(self):
        class Product(BaseModel):
            description: str

        assert validate_vector_field("description", Product) is True

    def test_valid_optional_string_field(self):
        class Product(BaseModel):
            description: Optional[str]

        assert validate_vector_field("description", Product) is True

    def test_invalid_int_field(self):
        class Product(BaseModel):
            price: int

        assert validate_vector_field("price", Product) is False

    def test_nonexistent_field(self):
        class Product(BaseModel):
            name: str

        assert validate_vector_field("description", Product) is False


class TestAsyncBatch:
    """Tests for AsyncBatch helper class"""

    def test_initial_state(self):
        batch = AsyncBatch(max_size=10)
        assert len(batch) == 0
        assert batch.items == []

    def test_add_items_not_full(self):
        batch = AsyncBatch(max_size=3)
        assert batch.add("item1") is False
        assert batch.add("item2") is False
        assert len(batch) == 2

    def test_add_items_becomes_full(self):
        batch = AsyncBatch(max_size=3)
        batch.add("item1")
        batch.add("item2")
        assert batch.add("item3") is True
        assert len(batch) == 3

    def test_get_items_clears_batch(self):
        batch = AsyncBatch(max_size=10)
        batch.add("item1")
        batch.add("item2")
        items = batch.get_items()
        assert items == ["item1", "item2"]
        assert len(batch) == 0

    def test_multiple_batches(self):
        batch = AsyncBatch(max_size=2)
        batch.add("item1")
        batch.add("item2")
        first_batch = batch.get_items()
        batch.add("item3")
        batch.add("item4")
        second_batch = batch.get_items()
        assert first_batch == ["item1", "item2"]
        assert second_batch == ["item3", "item4"]

    def test_custom_max_size(self):
        batch = AsyncBatch(max_size=5)
        for i in range(4):
            assert batch.add(f"item{i}") is False
        assert batch.add("item4") is True
