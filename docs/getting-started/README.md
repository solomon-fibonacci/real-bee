# Getting Started with real-bee

Welcome to real-bee! This guide will help you get up and running quickly.

## What is real-bee?

**real-bee** (REAL-time Back-End on Events) is a high-performance FastAPI framework that automatically generates complete REST APIs with real-time capabilities and multimodal search from simple Pydantic schemas.

### Key Features

- **Auto-CRUD Generation**: Define a Pydantic schema → Get full REST API automatically
- **Real-time Updates**: WebSocket support with room-based broadcasting
- **Multimodal Search**: CLIP embeddings + FAISS for text and image similarity search
- **Event-Driven**: Redis pub/sub event bus for distributed systems
- **High Performance**: Async I/O, connection pooling, multi-level caching
- **Type-Safe**: Full Pydantic validation and type hints
- **Scalable**: Designed for horizontal scaling

## Quick Start

### Prerequisites

- Python 3.9-3.12
- PostgreSQL 13+
- Redis 6+
- (Optional) CUDA-capable GPU for faster embeddings

### Installation

See the complete [Installation Guide](installation.md) for detailed setup instructions.

```bash
# Clone the repository
git clone <repo-url>
cd real-bee

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Your First API

```python
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from realbee import CRUDFramework, FrameworkConfig

# 1. Define your data model
class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    price: float

    class Config:
        vector_fields = ["description"]

# 2. Initialize FastAPI
app = FastAPI(title="My API")

# 3. Configure framework
config = FrameworkConfig(
    postgres_url="postgresql://user:password@localhost:5432/mydb",
    redis_url="redis://localhost:6379/0",
)

# 4. Initialize framework
framework = CRUDFramework(app, config)

# 5. Register your model - this auto-generates all CRUD endpoints!
framework.register_entity(Product)
```

### Run the Application

```bash
uvicorn main:app --reload
```

That's it! You now have a complete REST API with:

- ✅ `POST /products` - Create product
- ✅ `GET /products` - List products (paginated)
- ✅ `GET /products/{id}` - Get product by ID
- ✅ `PATCH /products/{id}` - Update product
- ✅ `DELETE /products/{id}` - Delete product
- ✅ `POST /products/bulk` - Bulk create
- ✅ `POST /products/search` - Semantic search
- ✅ `WS /ws/products` - Real-time updates

## Next Steps

- **[Installation Guide](installation.md)** - Detailed setup instructions
- **[Architecture Overview](../architecture/overview.md)** - Learn how real-bee works
- **[Features Guide](../features/authentication.md)** - Explore advanced features
- **[Examples](/examples)** - Working code examples

## Project Structure

```
real-bee/
├── src/
│   └── realbee/          # Main package
│       ├── framework.py   # Main CRUDFramework class
│       ├── core.py        # Configuration and base classes
│       ├── database.py    # PostgreSQL manager
│       ├── cache.py       # Redis cache and pub/sub
│       ├── events.py      # Event bus
│       ├── search.py      # FAISS + CLIP search
│       ├── websocket.py   # WebSocket manager
│       ├── routes.py      # Route generation
│       └── ...
├── examples/             # Code examples
├── docs/                 # Documentation
├── tests/                # Test suite
├── requirements.txt      # Dependencies
└── pyproject.toml        # Project configuration
```

## Need Help?

- Check out the full [documentation index](../index.md)
- Review the [examples](/examples) directory
- Read the [architecture overview](../architecture/overview.md)

---

[Back to Documentation](../README.md)
