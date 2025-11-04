"""
Example Usage: Product catalog with multimodal search
"""
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel, Field

from framework.core import FrameworkConfig, searchable, IndexStrategy, EntityHooks
from framework.framework import CRUDFramework


# Define your entity schemas
class Product(BaseModel):
    """Product entity with multimodal search"""
    id: Optional[int] = None
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    image_url: Optional[str] = Field(None, description="Product image URL")
    price: float = Field(..., gt=0, description="Product price")
    category: str = Field(..., description="Product category")
    tags: List[str] = Field(default_factory=list, description="Product tags")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        # Framework will use these for vector search
        vector_fields = ["description", "image_url"]


class Review(BaseModel):
    """Product review"""
    id: Optional[int] = None
    product_id: int = Field(..., description="Product ID")
    user_id: int = Field(..., description="User ID")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str = Field(..., description="Review comment")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        vector_fields = ["comment"]


class User(BaseModel):
    """User entity"""
    id: Optional[int] = None
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Custom hooks example
class ProductHooks(EntityHooks):
    """Custom hooks for Product lifecycle"""
    
    @staticmethod
    def before_create(instance: Product) -> Product:
        """Validate before creating"""
        # Could add custom validation, data enrichment, etc.
        if instance.price < 0:
            raise ValueError("Price cannot be negative")
        return instance
    
    @staticmethod
    async def after_create(instance: Product) -> None:
        """After product is created"""
        # Could trigger external services, send notifications, etc.
        print(f"New product created: {instance.name}")
    
    @staticmethod
    async def before_delete(instance: Product) -> bool:
        """Prevent deletion of expensive products"""
        if instance.price > 10000:
            print(f"Preventing deletion of expensive product: {instance.name}")
            return False
        return True


# Initialize FastAPI app
app = FastAPI(title="Product Catalog API", version="1.0.0")

# Configure framework
config = FrameworkConfig(
    # Database
    postgres_url="postgresql://user:password@localhost:5432/products",
    postgres_pool_size=20,
    
    # Redis
    redis_url="redis://localhost:6379/0",
    redis_pool_size=50,
    
    # FAISS
    faiss_index_type="IndexFlatIP",
    faiss_dimension=512,
    faiss_nprobe=10,
    
    # WebSocket
    ws_heartbeat_interval=30,
    ws_max_connections=10000,
    
    # Performance
    batch_size=100,
    max_concurrent_tasks=50,
    cache_enabled=True,
    
    # CLIP
    clip_model="ViT-B/32",
    clip_device="cuda"  # Use "cpu" if no GPU
)

# Initialize framework
framework = CRUDFramework(app, config)

# Register entities - this auto-generates all CRUD endpoints!
framework.register_entity(Product, hooks=ProductHooks())
framework.register_entity(Review)
framework.register_entity(User)

# That's it! The framework has now created:
# 
# Product endpoints:
#   POST   /products           - Create product
#   GET    /products           - List products
#   GET    /products/{id}      - Get product
#   PATCH  /products/{id}      - Update product
#   DELETE /products/{id}      - Delete product
#   POST   /products/bulk      - Bulk create
#   POST   /products/search    - Multimodal search
#   WS     /ws/products        - Real-time updates
#
# Review endpoints:
#   POST   /reviews            - Create review
#   GET    /reviews            - List reviews
#   GET    /reviews/{id}       - Get review
#   PATCH  /reviews/{id}       - Update review
#   DELETE /reviews/{id}       - Delete review
#   POST   /reviews/bulk       - Bulk create
#   POST   /reviews/search     - Multimodal search
#   WS     /ws/reviews         - Real-time updates
#
# User endpoints:
#   POST   /users              - Create user
#   GET    /users              - List users
#   GET    /users/{id}         - Get user
#   PATCH  /users/{id}         - Update user
#   DELETE /users/{id}         - Delete user
#   POST   /users/bulk         - Bulk create
#   WS     /ws/users           - Real-time updates


# Optional: Add custom endpoints
@app.get("/")
async def root():
    """API root"""
    return {
        "message": "Product Catalog API",
        "version": "1.0.0",
        "entities": ["products", "reviews", "users"]
    }


@app.get("/stats")
async def stats():
    """Get framework statistics"""
    return {
        "websocket": framework.ws_manager.get_stats(),
        "registered_entities": list(framework._metadata.keys())
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
