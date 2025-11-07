# Quick Start Guide

Get your API up and running in 5 minutes!

## Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Redis 6+
- (Optional) CUDA-capable GPU for faster embeddings

## Step 1: Installation

```bash
# Clone or download the framework
cd framework

# Install dependencies
pip install -r requirements.txt

# For GPU support (optional but recommended)
pip install faiss-gpu torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Step 2: Setup Infrastructure

### Option A: Using Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

```bash
docker-compose up -d
```

### Option B: Local Installation

```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Install Redis
brew install redis  # macOS
sudo apt install redis  # Ubuntu

# Start services
brew services start postgresql  # macOS
brew services start redis
```

## Step 3: Create Your First API

Create `my_app.py`:

```python
from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel
from framework import CRUDFramework, FrameworkConfig

# 1. Define your data model
class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    completed: bool = False
    tags: List[str] = []
    
    class Config:
        # Enable semantic search on description
        vector_fields = ["description"]

# 2. Initialize FastAPI
app = FastAPI(title="Task Manager API")

# 3. Configure framework
config = FrameworkConfig(
    postgres_url="postgresql://user:password@localhost:5432/mydb",
    redis_url="redis://localhost:6379/0",
    clip_device="cuda"  # Use "cpu" if no GPU
)

# 4. Initialize framework
framework = CRUDFramework(app, config)

# 5. Register your model
framework.register_entity(Task)

# That's it! Your API is ready
```

## Step 4: Run Your API

```bash
uvicorn my_app:app --reload --host 0.0.0.0 --port 8000
```

## Step 5: Test Your API

### Using the Interactive Docs

Open http://localhost:8000/docs in your browser

### Using curl

```bash
# Create a task
curl -X POST "http://localhost:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn FastAPI",
    "description": "Master FastAPI framework for building APIs",
    "tags": ["learning", "programming"]
  }'

# List tasks
curl "http://localhost:8000/tasks"

# Get specific task
curl "http://localhost:8000/tasks/1"

# Update task
curl -X PATCH "http://localhost:8000/tasks/1" \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Search tasks semantically
curl -X POST "http://localhost:8000/tasks/search" \
  -H "Content-Type: application/json" \
  -d '{"text": "API development tutorials", "k": 5}'

# Delete task
curl -X DELETE "http://localhost:8000/tasks/1"
```

### Using Python

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create
        response = await client.post("/tasks", json={
            "title": "Buy groceries",
            "description": "Get milk, eggs, and bread from the store",
            "tags": ["shopping"]
        })
        task = response.json()
        print(f"Created task: {task['id']}")
        
        # Search
        response = await client.post("/tasks/search", params={
            "text": "grocery shopping",
            "k": 5
        })
        results = response.json()
        print(f"Found {len(results)} similar tasks")

asyncio.run(test_api())
```

## Step 6: Add Real-time Updates

### JavaScript Client

```html
<!DOCTYPE html>
<html>
<head>
    <title>Task Manager</title>
</head>
<body>
    <h1>Real-time Tasks</h1>
    <div id="tasks"></div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8000/ws/tasks');
        
        ws.onopen = () => {
            console.log('Connected to real-time updates');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'event') {
                console.log('Task updated:', data.data);
                // Update your UI here
                updateTaskList(data.data);
            }
        };
        
        // Keep connection alive
        setInterval(() => {
            ws.send(JSON.stringify({ type: 'ping' }));
        }, 30000);
        
        function updateTaskList(taskData) {
            // Update DOM with new task data
            const tasksDiv = document.getElementById('tasks');
            tasksDiv.innerHTML += `<div>${taskData.entity.title}</div>`;
        }
    </script>
</body>
</html>
```

## What You Get Automatically

After registering your `Task` model, you immediately have:

### REST Endpoints
- ✅ `POST /tasks` - Create task
- ✅ `GET /tasks` - List tasks with pagination
- ✅ `GET /tasks/{id}` - Get specific task
- ✅ `PATCH /tasks/{id}` - Update task
- ✅ `DELETE /tasks/{id}` - Delete task
- ✅ `POST /tasks/bulk` - Bulk create tasks
- ✅ `POST /tasks/search` - Semantic search

### WebSocket
- ✅ `WS /ws/tasks` - Real-time updates

### Features
- ✅ Automatic validation
- ✅ OpenAPI documentation
- ✅ Redis caching
- ✅ Event notifications
- ✅ Vector search
- ✅ Error handling

## Next Steps

### Add Lifecycle Hooks

```python
from framework import EntityHooks

class TaskHooks(EntityHooks):
    @staticmethod
    def before_create(instance: Task) -> Task:
        # Add created timestamp, validate, etc.
        return instance
    
    @staticmethod
    async def after_create(instance: Task):
        # Send notification
        print(f"New task created: {instance.title}")

framework.register_entity(Task, hooks=TaskHooks())
```

### Add Custom Routes

```python
@app.get("/tasks/completed")
async def get_completed_tasks():
    repo = framework.get_repository("Task")
    return await repo.list(filters={"completed": True})
```

### Add Multiple Entities

```python
class User(BaseModel):
    id: Optional[int] = None
    email: str
    name: str

class Comment(BaseModel):
    id: Optional[int] = None
    task_id: int
    user_id: int
    text: str
    
    class Config:
        vector_fields = ["text"]

framework.register_entity(User)
framework.register_entity(Comment)
```

Now you have:
- `/tasks`, `/users`, `/comments` endpoints
- `/ws/tasks`, `/ws/users`, `/ws/comments` WebSockets
- Semantic search across all entities

## Common Issues

### 1. CLIP Model Download Slow
First run downloads ~350MB model. Subsequent runs are fast.

### 2. Port Already in Use
```bash
# Change port
uvicorn my_app:app --port 8001
```

### 3. Database Connection Error
```bash
# Verify PostgreSQL is running
pg_isready

# Check connection string
psql "postgresql://user:password@localhost:5432/mydb"
```

### 4. Redis Connection Error
```bash
# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

## Production Checklist

- [ ] Add authentication middleware
- [ ] Configure CORS for your domain
- [ ] Enable HTTPS/TLS
- [ ] Setup monitoring (Prometheus)
- [ ] Configure logging
- [ ] Use production database
- [ ] Setup Redis Cluster
- [ ] Add rate limiting
- [ ] Setup backups
- [ ] Load testing

## Resources

- **API Docs**: http://localhost:8000/docs
- **Framework Docs**: See README.md
- **Performance Guide**: See PERFORMANCE.md
- **Architecture**: See ARCHITECTURE.md

## Support

For issues or questions:
1. Check the documentation
2. Review example.py for patterns
3. Check PERFORMANCE.md for optimization tips

## Congratulations! 🎉

You now have a production-ready API with:
- Full CRUD operations
- Real-time updates
- Semantic search
- Caching
- Event-driven architecture

All from a simple Pydantic schema!
