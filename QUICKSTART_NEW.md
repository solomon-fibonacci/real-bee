# Quick Start Guide - real-bee

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd real-bee

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Basic Usage

### 1. Define Your Entity Schema

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class Product(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0)
    category: str
    tags: List[str] = []

    class Config:
        # These fields will be indexed for multimodal search
        vector_fields = ["description"]
```

### 2. Initialize the Framework

```python
from fastapi import FastAPI
from realbee import CRUDFramework, FrameworkConfig

app = FastAPI(title="My API")

# Configure the framework
config = FrameworkConfig(
    postgres_url="postgresql://user:password@localhost:5432/mydb",
    redis_url="redis://localhost:6379/0",
)

# Initialize framework
framework = CRUDFramework(app, config)

# Register your entities - this auto-generates all CRUD endpoints!
framework.register_entity(Product)
```

### 3. Run the Application

```bash
uvicorn main:app --reload
```

That's it! You now have:

**REST Endpoints:**
- `POST /products` - Create product
- `GET /products` - List products (paginated)
- `GET /products/{id}` - Get product by ID
- `PATCH /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product
- `POST /products/bulk` - Bulk create
- `POST /products/search` - Search products (if vector_fields configured)

**WebSocket:**
- `WS /ws/products` - Real-time updates

## Project Structure

```
real-bee/
├── src/
│   └── realbee/          # Main package
│       ├── __init__.py
│       ├── framework.py   # Main CRUDFramework class
│       ├── core.py        # Configuration and base classes
│       ├── database.py    # PostgreSQL manager
│       ├── cache.py       # Redis cache and pub/sub
│       ├── events.py      # Event bus
│       ├── search.py      # FAISS + CLIP search
│       ├── websocket.py   # WebSocket manager
│       ├── routes.py      # Route generation
│       ├── models.py      # Data models
│       ├── utils.py       # Utilities
│       └── exceptions.py  # Custom exceptions
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Next Steps

- Check out the full documentation in README.md
- See example.py for a complete working example
- Read ARCHITECTURE.md to understand the system design
- Explore AUTHENTICATION.md for security features
