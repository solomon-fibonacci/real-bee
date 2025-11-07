"""
Simple example showing how to use real-bee framework
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import FastAPI

# Import from the realbee package
from src.realbee import CRUDFramework, FrameworkConfig, EntityHooks


# Define your entity
class Product(BaseModel):
    """Simple product entity"""
    id: Optional[int] = None
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0)
    category: str

    class Config:
        # Enable search on description field
        vector_fields = ["description"]


# Optional: Define custom hooks
class ProductHooks(EntityHooks):
    @staticmethod
    def before_create(instance: Product) -> Product:
        print(f"Creating product: {instance.name}")
        return instance

    @staticmethod
    async def after_create(instance: Product):
        print(f"Product created with ID: {instance.id}")


# Create FastAPI app
app = FastAPI(title="Product API", version="1.0.0")

# Configure framework
config = FrameworkConfig(
    postgres_url="postgresql://postgres:postgres@localhost:5432/realbee",
    redis_url="redis://localhost:6379/0",
    cache_enabled=True,
)

# Initialize framework
framework = CRUDFramework(app, config)

# Register entity - this auto-generates all CRUD endpoints!
framework.register_entity(Product, hooks=ProductHooks())


# Optional: Add custom endpoints
@app.get("/")
async def root():
    return {
        "message": "Welcome to real-bee!",
        "docs": "/docs",
        "entities": list(framework.metadata.keys())
    }


@app.get("/stats")
async def stats():
    """Get framework statistics"""
    return {
        "websocket_stats": framework.ws_manager.get_stats(),
        "registered_entities": list(framework.metadata.keys()),
        "recent_events": [
            e.model_dump() for e in framework.event_bus.get_recent_events(limit=10)
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("""
    🐝 Starting real-bee example server...

    Available endpoints:
    - POST   /products           - Create product
    - GET    /products           - List products
    - GET    /products/{id}      - Get product
    - PATCH  /products/{id}      - Update product
    - DELETE /products/{id}      - Delete product
    - POST   /products/bulk      - Bulk create
    - POST   /products/search    - Search products
    - WS     /ws/products        - Real-time updates

    Documentation: http://localhost:8000/docs
    """)

    uvicorn.run(
        "example_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
