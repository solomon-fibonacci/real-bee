"""
Factory classes for generating test data
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import random


# ============================================================================
# Test Entity Schemas
# ============================================================================

class Product(BaseModel):
    """Product entity for testing"""
    id: Optional[int] = None
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0)
    category: str
    tags: List[str] = []

    class Config:
        vector_fields = ["description"]


class User(BaseModel):
    """User entity for testing"""
    id: Optional[int] = None
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    avatar_url: Optional[str] = None


class Review(BaseModel):
    """Review entity for testing"""
    id: Optional[int] = None
    product_id: int = Field(..., description="Product ID")
    user_id: int = Field(..., description="User ID")
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., description="Review comment")

    class Config:
        vector_fields = ["comment"]


# ============================================================================
# Factories
# ============================================================================

class ProductFactory:
    """Factory for creating test products"""

    _counter = 0

    @classmethod
    def build(cls, **kwargs) -> Product:
        """Build a single product"""
        cls._counter += 1

        defaults = {
            "name": f"Test Product {cls._counter}",
            "description": f"This is a test product description for product {cls._counter}",
            "price": round(random.uniform(10.0, 1000.0), 2),
            "category": random.choice(["Electronics", "Clothing", "Books", "Home", "Sports"]),
            "tags": [f"tag{i}" for i in range(random.randint(1, 4))],
        }

        defaults.update(kwargs)
        return Product(**defaults)

    @classmethod
    def build_batch(cls, count: int, **kwargs) -> List[Product]:
        """Build multiple products"""
        return [cls.build(**kwargs) for _ in range(count)]

    @classmethod
    def reset(cls):
        """Reset counter"""
        cls._counter = 0


class UserFactory:
    """Factory for creating test users"""

    _counter = 0

    @classmethod
    def build(cls, **kwargs) -> User:
        """Build a single user"""
        cls._counter += 1

        defaults = {
            "email": f"user{cls._counter}@test.com",
            "name": f"Test User {cls._counter}",
            "avatar_url": f"https://example.com/avatar{cls._counter}.jpg",
        }

        defaults.update(kwargs)
        return User(**defaults)

    @classmethod
    def build_batch(cls, count: int, **kwargs) -> List[User]:
        """Build multiple users"""
        return [cls.build(**kwargs) for _ in range(count)]

    @classmethod
    def reset(cls):
        """Reset counter"""
        cls._counter = 0


class ReviewFactory:
    """Factory for creating test reviews"""

    _counter = 0

    @classmethod
    def build(cls, **kwargs) -> Review:
        """Build a single review"""
        cls._counter += 1

        defaults = {
            "product_id": random.randint(1, 100),
            "user_id": random.randint(1, 100),
            "rating": random.randint(1, 5),
            "comment": f"This is a test review comment number {cls._counter}",
        }

        defaults.update(kwargs)
        return Review(**defaults)

    @classmethod
    def build_batch(cls, count: int, **kwargs) -> List[Review]:
        """Build multiple reviews"""
        return [cls.build(**kwargs) for _ in range(count)]

    @classmethod
    def reset(cls):
        """Reset counter"""
        cls._counter = 0
