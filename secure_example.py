"""
Example with Authentication: Secure Product Catalog API
"""
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel, Field

from framework.core import FrameworkConfig
from framework.secure_framework import SecureCRUDFramework
from framework.auth import AuthConfig, Role, Permission


# Define your entity schemas
class Product(BaseModel):
    """Product entity - requires authentication"""
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
        vector_fields = ["description", "image_url"]


class Review(BaseModel):
    """Product review - anyone can read, authenticated users can write"""
    id: Optional[int] = None
    product_id: int = Field(..., description="Product ID")
    user_id: int = Field(..., description="User ID")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str = Field(..., description="Review comment")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        vector_fields = ["comment"]


class Article(BaseModel):
    """Public article - anyone can read"""
    id: Optional[int] = None
    title: str
    content: str
    author: str
    published_at: Optional[datetime] = None
    
    class Config:
        vector_fields = ["content"]


# Initialize FastAPI app
app = FastAPI(
    title="Secure Product Catalog API",
    version="1.0.0",
    description="Product catalog with authentication and authorization"
)

# Configure framework
config = FrameworkConfig(
    # Database
    postgres_url="postgresql://user:password@localhost:5432/secure_products",
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
    cache_enabled=True,
    
    # CLIP
    clip_model="ViT-B/32",
    clip_device="cuda"  # Use "cpu" if no GPU
)

# Configure authentication
auth_config = AuthConfig(
    secret_key="your-secret-key-change-in-production",  # CHANGE THIS!
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
    require_email_verification=False,  # Set to True in production
    max_failed_attempts=5,
    lockout_duration_minutes=30
)

# Initialize secure framework
framework = SecureCRUDFramework(
    app,
    config,
    auth_config=auth_config,
    enable_auth=True
)

# Register entities with different permissions

# Products - Authenticated users can read, only admins/moderators can write
framework.register_entity(
    Product,
    public_read=False,  # Requires authentication to read
    public_search=False  # Requires authentication to search
)

# Reviews - Public read, authenticated write
framework.register_entity(
    Review,
    public_read=True,  # Anyone can read reviews
    public_search=True  # Anyone can search reviews
)

# Articles - Fully public
framework.register_entity(
    Article,
    public_read=True,
    public_search=True
)


# Authentication routes are automatically created:
# POST   /auth/register         - Register new user
# POST   /auth/token           - Login (get JWT token)
# GET    /auth/me              - Get current user
# PUT    /auth/me              - Update current user
# POST   /auth/me/change-password - Change password
# GET    /auth/users           - List users (admin only)
# GET    /auth/users/{id}      - Get user (admin only)
# PUT    /auth/users/{id}      - Update user (admin only)


# Custom endpoints with permissions
@app.get("/")
async def root():
    """Public root endpoint"""
    return {
        "message": "Secure Product Catalog API",
        "version": "1.0.0",
        "auth": "enabled",
        "entities": ["products", "reviews", "articles"],
        "docs": "/docs"
    }


@app.get("/stats")
async def stats():
    """Get framework statistics (public)"""
    return {
        "websocket": framework.ws_manager.get_stats(),
        "registered_entities": list(framework._metadata.keys()),
        "authentication": "enabled"
    }


# Custom endpoint with role-based access
from fastapi import Depends
from framework.auth import User

@app.get("/admin/dashboard")
async def admin_dashboard(
    current_user: User = Depends(framework.auth_manager.require_role(Role.ADMIN, Role.SUPERADMIN))
):
    """Admin dashboard (admin only)"""
    return {
        "user": current_user.username,
        "role": [r.value for r in current_user.roles],
        "total_users": len(framework.auth_manager._users),
        "entities": list(framework._metadata.keys())
    }


# Custom endpoint with specific scope
@app.get("/products/featured")
async def get_featured_products(
    current_user: User = Depends(
        framework.auth_manager.require_scopes("product:read")
    )
):
    """Get featured products (requires product:read scope)"""
    repo = framework.get_repository("Product")
    # Custom query logic
    products = await repo.list(limit=10)
    
    return {
        "featured": products[:5],
        "requested_by": current_user.username
    }


if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          Secure Product Catalog API                          ║
    ╚══════════════════════════════════════════════════════════════╝
    
    🔐 Authentication Enabled
    
    Default Admin Credentials:
    - Username: admin
    - Password: admin123
    
    ⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!
    
    API Documentation: http://localhost:8000/docs
    
    Quick Start:
    1. Register a user:    POST /auth/register
    2. Get token:          POST /auth/token
    3. Use token in header: Authorization: Bearer <token>
    4. Access protected endpoints
    
    Roles:
    - USER: Can read/write their own data
    - MODERATOR: Can read all data, moderate content
    - ADMIN: Full access to all entities
    - SUPERADMIN: Full system access
    
    Scopes:
    - product:read, product:write, product:delete
    - review:read, review:write, review:delete
    - article:read, article:write, article:delete
    - user:read, user:write, user:delete
    - admin (full access)
    """)
    
    uvicorn.run(
        "secure_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
