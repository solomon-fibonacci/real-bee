# real-bee Examples

This directory contains working examples demonstrating various features of the real-bee framework.

## Examples Overview

### Basic Examples

#### `example_simple.py`
**Minimal working example** - The simplest way to get started with real-bee.

- Single entity (Product)
- Basic configuration
- Auto-generated CRUD endpoints
- Perfect for learning the basics

**Run it:**
```bash
python examples/example_simple.py
# Visit http://localhost:8000/docs
```

#### `example.py`
**Full-featured example** - Comprehensive demonstration of framework capabilities.

Features demonstrated:
- Multiple entities (Product, Review, User)
- Lifecycle hooks (before/after create, update, delete)
- Custom routes
- Statistics endpoint
- Real-time updates
- Multimodal search
- Event subscriptions

**Run it:**
```bash
python examples/example.py
# Visit http://localhost:8000/docs
```

### Client Examples

#### `client_example.py`
**Client usage patterns** - How to interact with the API from Python.

Demonstrates:
- REST API calls (CRUD operations)
- Bulk operations
- Multimodal search (text and image)
- WebSocket connections
- Real-time event handling
- Pagination

**Run it:**
```bash
# First, start the API server
python examples/example.py

# Then in another terminal
python examples/client_example.py
```

### Authentication Examples

#### `secure_example.py`
**API with authentication** - Complete OAuth2 + JWT authentication example.

Features:
- User registration and login
- JWT token authentication
- Role-based access control (RBAC)
- Protected endpoints
- Public vs authenticated access
- Multiple entities with different permission levels

**Run it:**
```bash
python examples/secure_example.py
# Visit http://localhost:8000/docs
# Try the /auth/register and /auth/token endpoints
```

#### `secure_client_example.py`
**Authenticated client** - How to use authentication from the client side.

Demonstrates:
- User registration
- Login and token management
- Using JWT tokens for authenticated requests
- Handling 401/403 errors
- Token refresh patterns
- Protected resource access

**Run it:**
```bash
# First, start the secure API server
python examples/secure_example.py

# Then in another terminal
python examples/secure_client_example.py
```

## Prerequisites

Before running the examples, ensure you have:

1. **PostgreSQL** running on `localhost:5432`
2. **Redis** running on `localhost:6379`
3. **Python dependencies** installed: `pip install -r requirements.txt`

### Quick Setup with Docker

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.test.yml up -d

# Or use individual containers
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
docker run -d -p 6379:6379 redis:7
```

## Usage Patterns

### Running an Example

```bash
# From the project root
python examples/example.py

# Or specify the full path
cd /path/to/real-bee
python examples/example.py
```

### Testing the API

Once an example is running:

1. **Interactive Docs**: Open http://localhost:8000/docs
2. **ReDoc**: Open http://localhost:8000/redoc
3. **Direct API calls**: Use curl, httpx, or the client examples

### Using curl

```bash
# Create a product
curl -X POST "http://localhost:8000/products" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Product",
    "description": "A sample product",
    "price": 19.99
  }'

# List products
curl "http://localhost:8000/products"

# Search products
curl -X POST "http://localhost:8000/products/search" \
  -H "Content-Type: application/json" \
  -d '{"text": "sample product", "k": 5}'
```

## Example Modification Guide

### Adding Your Own Entity

```python
# 1. Define your Pydantic model
from pydantic import BaseModel
from typing import Optional

class MyEntity(BaseModel):
    id: Optional[int] = None
    name: str
    description: str

    class Config:
        vector_fields = ["description"]  # Enable search

# 2. Register it with the framework
framework.register_entity(MyEntity)

# 3. Done! You now have:
# - POST /myentity
# - GET /myentity
# - GET /myentity/{id}
# - PATCH /myentity/{id}
# - DELETE /myentity/{id}
# - POST /myentity/search
# - WS /ws/myentity
```

### Adding Lifecycle Hooks

```python
from realbee import EntityHooks

class MyEntityHooks(EntityHooks):
    @staticmethod
    def before_create(instance: MyEntity) -> MyEntity:
        # Modify before creation
        instance.name = instance.name.strip().title()
        return instance

    @staticmethod
    async def after_create(instance: MyEntity):
        # Execute after creation
        print(f"Created: {instance.name}")

framework.register_entity(MyEntity, hooks=MyEntityHooks())
```

### Adding Custom Routes

```python
@app.get("/myentity/stats")
async def get_stats():
    repo = framework.get_repository("MyEntity")
    count = await repo.count()
    return {"total": count}
```

## Troubleshooting

### "Connection refused" errors

Ensure PostgreSQL and Redis are running:
```bash
# Check PostgreSQL
pg_isready -h localhost -p 5432

# Check Redis
redis-cli -h localhost -p 6379 ping
```

### "ModuleNotFoundError"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "Table already exists"

The examples create tables automatically. If you want a fresh start:
```bash
# Connect to PostgreSQL
psql -U postgres

# Drop and recreate database
DROP DATABASE IF EXISTS mydb;
CREATE DATABASE mydb;
```

### CLIP model download slow

The first run downloads ~350MB CLIP model. Subsequent runs are fast. For faster downloads:
```bash
# Set cache directory
export TORCH_HOME=/path/to/cache
```

## Next Steps

After exploring the examples:

1. **Read the documentation**: See [docs/](../docs/)
2. **Learn about architecture**: See [Architecture Overview](../docs/architecture/overview.md)
3. **Optimize performance**: See [Performance Guide](../docs/guides/performance.md)
4. **Add authentication**: See [Authentication Guide](../docs/features/authentication.md)
5. **Write tests**: See [Testing Guide](../docs/guides/testing.md)

## Learning Path

1. **Start simple**: Run `example_simple.py` to understand the basics
2. **Explore features**: Run `example.py` to see advanced features
3. **Try the client**: Run `client_example.py` to learn API interaction
4. **Add security**: Run `secure_example.py` for authentication
5. **Build your app**: Use examples as templates for your project

## Additional Resources

- **[Getting Started Guide](../docs/getting-started/)** - Detailed setup
- **[Documentation Index](../docs/index.md)** - All documentation
- **[API Reference](../docs/api/)** - API documentation
- **[GitHub Issues](https://github.com/solomon-fibonacci/real-bee/issues)** - Report bugs or request features

---

Happy coding with real-bee! 🚀
