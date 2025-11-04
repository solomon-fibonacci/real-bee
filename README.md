# Realtime-CRUD-REST-MultimodalSearch Framework

A high-performance, event-driven framework that automatically generates CRUD endpoints with real-time capabilities and multimodal search for any Pydantic schema.

## 🚀 Features

- **Auto-CRUD Generation**: Define a Pydantic schema → Get full REST API automatically
- **Real-time Updates**: WebSocket support with room-based broadcasting
- **Multimodal Search**: CLIP embeddings + FAISS for text and image similarity search
- **Event-Driven**: Redis pub/sub event bus for distributed systems
- **High Performance**: Async I/O, connection pooling, multi-level caching
- **Type-Safe**: Full Pydantic validation and type hints
- **Scalable**: Designed for horizontal scaling

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Layer                          │
│  Auto-generated REST + WebSocket endpoints                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴─────────────────────────────┐
│                      Event Bus (Redis)                     │
│  Pub/Sub for real-time notifications                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼────────┐
│   PostgreSQL   │   │   Redis Cache   │   │  FAISS Index   │
│  Primary Store │   │  + Pub/Sub      │   │  Vector Search │
└────────────────┘   └─────────────────┘   └────────────────┘
        │                                            │
        └────────────────┬───────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │  CLIP Model │
                  │  Embeddings │
                  └─────────────┘
```

## 📦 Installation

```bash
# Clone the repository
git clone <repo-url>
cd framework

# Install dependencies
pip install -r requirements.txt

# For GPU support (optional, significantly faster)
pip install faiss-gpu torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## 🔧 Setup

### 1. Database Setup

```bash
# PostgreSQL
createdb products_db

# Redis
redis-server
```

### 2. Configuration

```python
from framework.core import FrameworkConfig

config = FrameworkConfig(
    # Database
    postgres_url="postgresql://user:password@localhost:5432/db_name",
    postgres_pool_size=20,
    
    # Redis
    redis_url="redis://localhost:6379/0",
    redis_pool_size=50,
    
    # FAISS
    faiss_index_type="IndexFlatIP",  # Cosine similarity
    faiss_dimension=512,              # CLIP ViT-B/32 dimension
    
    # CLIP
    clip_model="ViT-B/32",
    clip_device="cuda"  # or "cpu"
)
```

## 🎯 Quick Start

### Define Your Schema

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    image_url: Optional[str] = None
    price: float
    category: str
    tags: List[str] = []
    
    class Config:
        # These fields will be embedded and indexed for search
        vector_fields = ["description", "image_url"]
```

### Initialize Framework

```python
from fastapi import FastAPI
from framework.framework import CRUDFramework

app = FastAPI()
framework = CRUDFramework(app, config)

# Register entity - this creates all endpoints!
framework.register_entity(Product)
```

### That's It!

You now have:

**REST Endpoints:**
- `POST /products` - Create product
- `GET /products` - List products (with pagination)
- `GET /products/{id}` - Get product by ID
- `PATCH /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product
- `POST /products/bulk` - Bulk create
- `POST /products/search` - Multimodal search

**WebSocket:**
- `WS /ws/products` - Real-time updates

## 🔍 Multimodal Search

### Text Search
```python
# Search by description
POST /products/search
{
    "text": "comfortable running shoes",
    "k": 10
}
```

### Image Search
```python
# Search by image
POST /products/search
{
    "image_url": "https://example.com/shoe.jpg",
    "k": 10
}
```

### Hybrid Search
```python
# Combine text and image
POST /products/search
{
    "text": "red athletic shoes",
    "image_url": "https://example.com/reference.jpg",
    "text_weight": 0.7,  # 70% text, 30% image
    "k": 10
}
```

## 🔴 Real-time Updates

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/products');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'event') {
        console.log('Entity updated:', data.data);
        // Update UI in real-time
    }
};

// Keep connection alive
setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

### Python Client

```python
import asyncio
import websockets
import json

async def listen_for_updates():
    async with websockets.connect('ws://localhost:8000/ws/products') as ws:
        async for message in ws:
            data = json.loads(message)
            print('Update:', data)

asyncio.run(listen_for_updates())
```

## 🎣 Lifecycle Hooks

Add custom logic to entity lifecycle:

```python
from framework.core import EntityHooks

class ProductHooks(EntityHooks):
    @staticmethod
    def before_create(instance: Product) -> Product:
        # Validate, enrich, or modify before creation
        instance.name = instance.name.upper()
        return instance
    
    @staticmethod
    async def after_create(instance: Product):
        # Trigger external services, send notifications
        await send_notification(f"New product: {instance.name}")
    
    @staticmethod
    async def before_delete(instance: Product) -> bool:
        # Prevent deletion if conditions not met
        if instance.price > 10000:
            return False  # Don't delete expensive items
        return True

# Register with hooks
framework.register_entity(Product, hooks=ProductHooks())
```

## ⚡ Performance Features

### Multi-level Caching
- Redis cache for frequently accessed entities
- Configurable TTL per entity type
- Automatic cache invalidation on updates

### Connection Pooling
- PostgreSQL connection pooling (20 connections default)
- Redis connection pooling (50 connections default)

### Bulk Operations
```python
# More efficient than individual creates
POST /products/bulk
[
    {"name": "Product 1", "price": 10.0, ...},
    {"name": "Product 2", "price": 20.0, ...},
    ...
]
```

### Async Throughout
- Full async/await support
- Non-blocking I/O operations
- Concurrent request handling

## 🔐 Advanced Features

### Custom Routes

```python
@app.get("/products/featured")
async def get_featured_products():
    repo = framework.get_repository("Product")
    # Custom query logic
    return await repo.list(limit=10, filters={"featured": True})
```

### Event Subscriptions

```python
# Subscribe to specific events
@framework.event_bus.on("Product", EventType.CREATED)
async def on_product_created(event: Event):
    print(f"New product: {event.entity_id}")
    # Trigger webhook, update cache, etc.
```

### Search Index Management

```python
# Save index to disk
await framework.search_engine.save_index("Product", "/data/product.index")

# Load index from disk
await framework.search_engine.load_index("Product", "/data/product.index")
```

## 📊 Monitoring

```python
@app.get("/stats")
async def get_stats():
    return {
        "websocket": framework.ws_manager.get_stats(),
        "entities": list(framework._metadata.keys())
    }
```

Returns:
```json
{
    "websocket": {
        "total_connections": 150,
        "total_rooms": 45,
        "connections_by_entity": {
            "Product": 100,
            "Review": 50
        }
    },
    "entities": ["Product", "Review", "User"]
}
```

## 🚀 Running

```bash
# Development
uvicorn example:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn example:app --workers 4 --host 0.0.0.0 --port 8000
```

## 🧪 Testing

```bash
# Run example client
python client_example.py

# Run tests
pytest tests/
```

## 📈 Scalability

### Horizontal Scaling
- Stateless design allows multiple instances
- Redis pub/sub for cross-instance events
- PostgreSQL read replicas for read-heavy workloads
- FAISS index sharding for large datasets

### Load Balancing
```nginx
upstream api {
    least_conn;
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    location / {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🔧 Configuration Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `postgres_pool_size` | 20 | Database connection pool size |
| `redis_pool_size` | 50 | Redis connection pool size |
| `faiss_index_type` | "IndexFlatIP" | FAISS index type |
| `faiss_dimension` | 512 | Embedding dimension |
| `clip_model` | "ViT-B/32" | CLIP model variant |
| `ws_max_connections` | 10000 | Max WebSocket connections |
| `cache_ttl` | 300 | Cache TTL in seconds |
| `batch_size` | 100 | Batch operation size |

## 🐛 Troubleshooting

### CLIP Model Loading Slow
- First run downloads ~350MB model
- Use GPU for faster inference
- Cache model: `TORCH_HOME=/path/to/cache`

### WebSocket Disconnects
- Check heartbeat interval
- Verify firewall settings
- Use sticky sessions with load balancer

### Search Results Empty
- Wait for embeddings to be generated (async)
- Check vector_fields configuration
- Verify CLIP model loaded successfully

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## 📚 Examples

See `example.py` for a complete working example with Products, Reviews, and Users.

See `client_example.py` for client usage patterns.
