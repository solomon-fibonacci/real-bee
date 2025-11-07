# real-bee

**REAL-time Back-End on Events** - A high-performance, event-driven framework that automatically generates CRUD endpoints with real-time capabilities and multimodal search for any Pydantic schema.

[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🚀 Features

- **Auto-CRUD Generation**: Define a Pydantic schema → Get full REST API automatically
- **Real-time Updates**: WebSocket support with room-based broadcasting
- **Multimodal Search**: CLIP embeddings + FAISS for text and image similarity search
- **Event-Driven**: Redis pub/sub event bus for distributed systems
- **High Performance**: Async I/O, connection pooling, multi-level caching
- **Type-Safe**: Full Pydantic validation and type hints
- **Scalable**: Designed for horizontal scaling
- **Authentication**: Built-in OAuth2 + JWT + RBAC support

## ⚡ Quick Start

### Define Your Schema

```python
from typing import Optional
from pydantic import BaseModel

class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    price: float

    class Config:
        vector_fields = ["description"]  # Enable semantic search
```

### Initialize Framework

```python
from fastapi import FastAPI
from realbee import CRUDFramework, FrameworkConfig

app = FastAPI()

config = FrameworkConfig(
    postgres_url="postgresql://user:password@localhost:5432/mydb",
    redis_url="redis://localhost:6379/0",
)

framework = CRUDFramework(app, config)
framework.register_entity(Product)
```

### That's It!

You now have a complete API with:

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

## 📦 Installation

```bash
# Clone the repository
git clone <repo-url>
cd real-bee

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Prerequisites

- Python 3.9-3.12
- PostgreSQL 13+
- Redis 6+
- (Optional) CUDA-capable GPU for faster embeddings

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
```

## 📚 Documentation

Complete documentation is available in the [`docs/`](docs/) directory:

- **[Getting Started](docs/getting-started/)** - Installation and first steps
- **[Architecture](docs/architecture/)** - System design and components
- **[Guides](docs/guides/)** - How-to guides (performance, testing)
- **[Features](docs/features/)** - Feature documentation (authentication, etc.)
- **[Documentation Index](docs/index.md)** - Complete navigation guide

### Quick Links

- [Installation Guide](docs/getting-started/installation.md) - Detailed setup instructions
- [Architecture Overview](docs/architecture/overview.md) - Learn how real-bee works
- [Performance Guide](docs/guides/performance.md) - Optimization strategies
- [Authentication Guide](docs/features/authentication.md) - OAuth2, JWT, RBAC
- [Testing Guide](docs/guides/testing.md) - Testing strategy

## 💻 Examples

Check the [`examples/`](examples/) directory for working examples:

- `example.py` - Full-featured example with Products, Reviews, and Users
- `example_simple.py` - Minimal working example
- `client_example.py` - Client usage patterns
- `secure_example.py` - With authentication
- `secure_client_example.py` - Authenticated client examples

## 🔍 Multimodal Search

```python
# Search by text
POST /products/search
{
    "text": "comfortable running shoes",
    "k": 10
}

# Search by image
POST /products/search
{
    "image_url": "https://example.com/shoe.jpg",
    "k": 10
}

# Hybrid search (text + image)
POST /products/search
{
    "text": "red athletic shoes",
    "image_url": "https://example.com/reference.jpg",
    "text_weight": 0.7,
    "k": 10
}
```

## 🔴 Real-time Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/products');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'event') {
        console.log('Entity updated:', data.data);
        // Update UI in real-time
    }
};
```

## 🎣 Lifecycle Hooks

```python
from realbee import EntityHooks

class ProductHooks(EntityHooks):
    @staticmethod
    def before_create(instance: Product) -> Product:
        instance.name = instance.name.upper()
        return instance

    @staticmethod
    async def after_create(instance: Product):
        await send_notification(f"New product: {instance.name}")

framework.register_entity(Product, hooks=ProductHooks())
```

## 🔐 Authentication

```python
from realbee import SecureCRUDFramework, AuthConfig

auth_config = AuthConfig(
    secret_key="your-secret-key",
    access_token_expire_minutes=30
)

framework = SecureCRUDFramework(
    app, config,
    auth_config=auth_config,
    enable_auth=True
)

# Protected entity
framework.register_entity(Product, public_read=False)
```

See the [Authentication Guide](docs/features/authentication.md) for details.

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=realbee --cov-report=html

# Specific test types
pytest tests/unit          # Fast unit tests
pytest tests/integration   # Integration tests
pytest tests/e2e          # End-to-end tests
```

See the [Testing Guide](docs/guides/testing.md) for details.

## 🚀 Running

```bash
# Development
uvicorn example:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn example:app --workers 4 --host 0.0.0.0 --port 8000
```

## 📈 Performance

- **Throughput**: 1000+ req/s on basic CRUD operations
- **Latency**: <10ms for cached reads, <50ms for database writes
- **Scalability**: Horizontal scaling with Redis pub/sub
- **Optimizations**: Connection pooling, multi-level caching, async I/O

See the [Performance Guide](docs/guides/performance.md) for optimization strategies.

## 🤝 Contributing

Contributions are welcome! Please check the [documentation](docs/) for guidelines.

## 📝 License

MIT

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [PostgreSQL](https://www.postgresql.org/) - Primary database
- [Redis](https://redis.io/) - Cache and pub/sub
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [CLIP](https://github.com/openai/CLIP) - Multimodal embeddings

---

**[📚 Read the Full Documentation](docs/)** | **[🚀 Get Started](docs/getting-started/)** | **[💻 View Examples](examples/)**
