# Authentication & Authorization Guide

Complete guide to the authentication and authorization system.

## Overview

The framework includes a comprehensive OAuth2-based authentication system with:

- **JWT Tokens**: Secure, stateless authentication
- **Role-Based Access Control (RBAC)**: Predefined user roles
- **Scope-Based Permissions**: Granular access control
- **Entity-Level Permissions**: Per-entity operation control
- **Password Security**: Bcrypt hashing, account lockout
- **Token Refresh**: Long-lived refresh tokens

## Quick Start

### 1. Enable Authentication

```python
from fastapi import FastAPI
from framework.secure_framework import SecureCRUDFramework
from framework.auth import AuthConfig

app = FastAPI()

auth_config = AuthConfig(
    secret_key="your-secret-key",  # Change in production!
    access_token_expire_minutes=30,
    require_email_verification=False
)

framework = SecureCRUDFramework(
    app,
    config=framework_config,
    auth_config=auth_config,
    enable_auth=True  # Enable authentication
)
```

### 2. Register an Entity with Permissions

```python
# Private entity (authentication required)
framework.register_entity(
    Product,
    public_read=False,   # Auth required for reads
    public_search=False  # Auth required for search
)

# Public read, authenticated write
framework.register_entity(
    Review,
    public_read=True,    # Anyone can read
    public_search=True   # Anyone can search
)
```

### 3. Use the API

```python
import httpx

# Register
response = httpx.post("http://localhost:8000/auth/register", json={
    "username": "john",
    "email": "john@example.com",
    "password": "SecurePass123"
})

# Login
response = httpx.post("http://localhost:8000/auth/token", data={
    "username": "john",
    "password": "SecurePass123"
})
token = response.json()["access_token"]

# Use token
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get("http://localhost:8000/products", headers=headers)
```

## Authentication Endpoints

All endpoints are automatically created when authentication is enabled.

### User Registration

```http
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "disabled": false,
  "roles": ["user"],
  "scopes": ["user:read", "user:write"],
  "email_verified": false
}
```

### Login (Get Token)

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=SecurePass123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "scope": "user:read user:write product:read"
}
```

### Get Current User

```http
GET /auth/me
Authorization: Bearer <token>
```

### Update Current User

```http
PUT /auth/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "full_name": "John Smith"
}
```

### Change Password

```http
POST /auth/me/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "OldPass123",
  "new_password": "NewPass123"
}
```

### List Users (Admin Only)

```http
GET /auth/users
Authorization: Bearer <admin-token>
```

### Get User by ID (Admin Only)

```http
GET /auth/users/{user_id}
Authorization: Bearer <admin-token>
```

### Update User (Admin Only)

```http
PUT /auth/users/{user_id}
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "roles": ["user", "moderator"],
  "scopes": ["product:read", "product:write"]
}
```

## Roles

The framework includes predefined roles with hierarchical permissions:

### Role Hierarchy

```
SUPERADMIN
    └─ ADMIN
        └─ MODERATOR
            └─ USER
                └─ ANONYMOUS
```

### Role Definitions

| Role | Description | Default Scopes |
|------|-------------|----------------|
| **SUPERADMIN** | Full system access | All scopes |
| **ADMIN** | Administrative access | All entity operations, user management |
| **MODERATOR** | Content moderation | Read all entities, write own content |
| **USER** | Standard user | Read/write own data |
| **ANONYMOUS** | Unauthenticated | None (public endpoints only) |

### Assigning Roles

```python
# During registration (programmatically)
user = await auth_manager.create_user(user_create)
user_db = await auth_manager.get_user(user.username)
user_db.roles = [Role.ADMIN]

# Via API (admin only)
PUT /auth/users/{user_id}
{
  "roles": ["user", "moderator"]
}
```

## Scopes

Scopes provide granular permission control.

### Standard Scopes

- `user:read` - Read user data
- `user:write` - Write user data
- `user:delete` - Delete user data
- `admin` - Full administrative access

### Entity Scopes (Auto-Generated)

When you register an entity, three scopes are automatically created:

- `{entity}:read` - Read entity data
- `{entity}:write` - Create/update entity data
- `{entity}:delete` - Delete entity data

**Example:**
```python
framework.register_entity(Product)
# Creates: product:read, product:write, product:delete
```

### Checking Scopes in Code

```python
from fastapi import Depends
from framework.auth import User

# Require specific scopes
@app.get("/products/featured")
async def featured_products(
    current_user: User = Depends(
        framework.auth_manager.require_scopes("product:read")
    )
):
    return {"message": "Access granted"}
```

### Requiring Roles

```python
from framework.auth import Role

@app.get("/admin/dashboard")
async def admin_dashboard(
    current_user: User = Depends(
        framework.auth_manager.require_role(Role.ADMIN, Role.SUPERADMIN)
    )
):
    return {"message": "Admin access"}
```

## Entity-Level Permissions

Control access at the entity operation level.

### Permission Levels

- `READ` - GET endpoints
- `WRITE` - POST, PATCH endpoints
- `DELETE` - DELETE endpoints
- `ADMIN` - Full access

### Configuration

```python
# Public reads, authenticated writes
framework.register_entity(
    Article,
    public_read=True,    # Anyone can read
    public_search=True   # Anyone can search
)

# Fully authenticated
framework.register_entity(
    Product,
    public_read=False,   # Auth required
    public_search=False  # Auth required
)
```

### Permission Matrix

| Operation | Required Scope | Public Option |
|-----------|---------------|---------------|
| GET /{entity} | `{entity}:read` | `public_read=True` |
| GET /{entity}/{id} | `{entity}:read` | `public_read=True` |
| POST /{entity} | `{entity}:write` | N/A |
| PATCH /{entity}/{id} | `{entity}:write` | N/A |
| DELETE /{entity}/{id} | `{entity}:delete` | N/A |
| POST /{entity}/search | `{entity}:read` | `public_search=True` |
| WS /ws/{entity} | `{entity}:read` | N/A |

## Security Features

### Password Security

- **Bcrypt Hashing**: Secure password storage
- **Minimum Length**: 8 characters (configurable)
- **No Plain Text**: Passwords never stored in plain text

### Account Lockout

```python
auth_config = AuthConfig(
    max_failed_attempts=5,           # Lock after 5 failed logins
    lockout_duration_minutes=30      # Lock for 30 minutes
)
```

### Token Expiration

```python
auth_config = AuthConfig(
    access_token_expire_minutes=30,  # Access token valid for 30 min
    refresh_token_expire_days=7      # Refresh token valid for 7 days
)
```

### Email Verification (Optional)

```python
auth_config = AuthConfig(
    require_email_verification=True  # Require email verification
)
```

## WebSocket Authentication

Authenticate WebSocket connections using query parameters:

```javascript
const token = "your-jwt-token";
const ws = new WebSocket(`ws://localhost:8000/ws/products?token=${token}`);
```

**Python:**
```python
import websockets

token = "your-jwt-token"
async with websockets.connect(f"ws://localhost:8000/ws/products?token={token}") as ws:
    async for message in ws:
        print(message)
```

## Advanced Usage

### Custom Permissions

Add custom permissions beyond standard CRUD:

```python
from fastapi import Depends
from framework.auth import User

async def check_owns_resource(
    resource_id: int,
    current_user: User = Depends(framework.auth_manager.get_current_user)
):
    """Check if user owns the resource"""
    resource = await get_resource(resource_id)
    if resource.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@app.patch("/resources/{resource_id}")
async def update_resource(
    resource_id: int,
    updates: dict,
    current_user: User = Depends(check_owns_resource)
):
    # User owns the resource, allow update
    pass
```

### Dynamic Scope Assignment

```python
# Grant additional scopes to a user
user = await auth_manager.get_user_by_id(user_id)
user.scopes.append("special:feature")

# Next login will include new scope
```

### Multi-Tenancy

```python
from fastapi import Depends, Header

async def get_tenant_id(x_tenant_id: str = Header(...)):
    return x_tenant_id

@app.get("/products")
async def get_products(
    tenant_id: str = Depends(get_tenant_id),
    current_user: User = Depends(auth_manager.get_current_user)
):
    # Filter by tenant
    return await get_products_for_tenant(tenant_id)
```

## Configuration Reference

### AuthConfig Parameters

```python
AuthConfig(
    # JWT
    secret_key: str                    # Secret key for JWT signing
    algorithm: str = "HS256"           # JWT algorithm
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Password
    password_schemes: List[str] = ["bcrypt"]
    
    # OAuth2
    token_url: str = "/auth/token"
    
    # Security
    require_email_verification: bool = False
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
)
```

## Best Practices

### 1. Use Strong Secret Keys

```python
import secrets

auth_config = AuthConfig(
    secret_key=secrets.token_urlsafe(32)  # Generate strong key
)
```

### 2. Change Default Admin Password

```python
# Immediately after first deployment
PUT /auth/users/1
{
  "password": "NewStrongPassword123!"
}
```

### 3. Enable HTTPS in Production

```python
# Use reverse proxy (Nginx, Caddy)
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. Set Short Token Expiration

```python
auth_config = AuthConfig(
    access_token_expire_minutes=15,  # Short-lived access tokens
    refresh_token_expire_days=7      # Use refresh tokens
)
```

### 5. Validate Input

```python
from pydantic import Field, validator

class UserCreate(BaseModel):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain number')
        return v
```

### 6. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/token")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(...):
    pass
```

### 7. Audit Logging

```python
@app.middleware("http")
async def audit_log(request, call_next):
    if request.url.path.startswith("/auth/"):
        logger.info(f"Auth request: {request.method} {request.url}")
    response = await call_next(request)
    return response
```

## Troubleshooting

### Token Expired

**Error:** `401 Unauthorized - Token expired`

**Solution:** Use refresh token or login again

### Insufficient Permissions

**Error:** `403 Forbidden - Not enough permissions`

**Solution:** Check required scopes and user roles

### Account Locked

**Error:** `423 Locked - Account locked until...`

**Solution:** Wait for lockout period or contact admin

### Invalid Credentials

**Error:** `401 Unauthorized - Incorrect username or password`

**Solution:** Check credentials, account may be locked after failed attempts

## Examples

See the complete examples:

- **[secure_example.py](secure_example.py)** - Full API with authentication
- **[secure_client_example.py](secure_client_example.py)** - Client usage demos

## Security Checklist

- [ ] Change default admin password
- [ ] Use strong secret key (32+ bytes)
- [ ] Enable HTTPS in production
- [ ] Set appropriate token expiration
- [ ] Enable email verification
- [ ] Implement rate limiting
- [ ] Add audit logging
- [ ] Regular security updates
- [ ] Monitor failed login attempts
- [ ] Backup user database

## Migration from Non-Auth

If you have an existing API without auth:

```python
# Before
framework = CRUDFramework(app, config)
framework.register_entity(Product)

# After
framework = SecureCRUDFramework(
    app, config,
    auth_config=AuthConfig(),
    enable_auth=True
)
framework.register_entity(
    Product,
    public_read=True  # Allow existing clients to read
)
```

---

**Authentication Status**: ✅ Production Ready  
**Security**: OAuth2 + JWT + RBAC + Scopes  
**Compliance**: Industry standard security practices
