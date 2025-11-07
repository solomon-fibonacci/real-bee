"""
Client Example: Using the API with Authentication
"""
import asyncio
import httpx
from typing import Optional


class SecureAPIClient:
    """Client for the secure API with authentication"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
        self.access_token: Optional[str] = None
    
    async def register(self, username: str, email: str, password: str, full_name: str = None):
        """Register a new user"""
        response = await self.client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name
        })
        response.raise_for_status()
        return response.json()
    
    async def login(self, username: str, password: str):
        """Login and store access token"""
        response = await self.client.post("/auth/token", data={
            "username": username,
            "password": password
        })
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        
        # Set default authorization header
        self.client.headers["Authorization"] = f"Bearer {self.access_token}"
        
        print(f"✓ Logged in as {username}")
        print(f"  Token expires in: {token_data['expires_in']}s")
        print(f"  Scopes: {token_data['scope']}")
        
        return token_data
    
    async def get_me(self):
        """Get current user info"""
        response = await self.client.get("/auth/me")
        response.raise_for_status()
        return response.json()
    
    async def update_me(self, updates: dict):
        """Update current user"""
        response = await self.client.put("/auth/me", json=updates)
        response.raise_for_status()
        return response.json()
    
    async def change_password(self, old_password: str, new_password: str):
        """Change password"""
        response = await self.client.post("/auth/me/change-password", json={
            "old_password": old_password,
            "new_password": new_password
        })
        response.raise_for_status()
        return response.json()
    
    # Product operations
    async def create_product(self, product_data: dict):
        """Create a product (requires authentication)"""
        response = await self.client.post("/products", json=product_data)
        response.raise_for_status()
        return response.json()
    
    async def get_products(self, limit: int = 10):
        """Get products (requires authentication)"""
        response = await self.client.get("/products", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    
    async def search_products(self, text: str = None, k: int = 10):
        """Search products (requires authentication)"""
        params = {"k": k}
        if text:
            params["text"] = text
        
        response = await self.client.post("/products/search", params=params)
        response.raise_for_status()
        return response.json()
    
    # Review operations (public read)
    async def get_reviews(self, limit: int = 10, authenticated: bool = False):
        """Get reviews (public, no auth required)"""
        # Clear auth header for public request
        if not authenticated:
            headers = dict(self.client.headers)
            headers.pop("Authorization", None)
            response = await self.client.get("/reviews", params={"limit": limit}, headers=headers)
        else:
            response = await self.client.get("/reviews", params={"limit": limit})
        
        response.raise_for_status()
        return response.json()
    
    async def create_review(self, review_data: dict):
        """Create a review (requires authentication)"""
        response = await self.client.post("/reviews", json=review_data)
        response.raise_for_status()
        return response.json()
    
    # Admin operations
    async def list_users(self):
        """List all users (admin only)"""
        response = await self.client.get("/auth/users")
        response.raise_for_status()
        return response.json()
    
    async def admin_dashboard(self):
        """Access admin dashboard (admin only)"""
        response = await self.client.get("/admin/dashboard")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()


# Demo functions
async def demo_user_registration_and_login():
    """Demo: User registration and login"""
    print("\n" + "="*60)
    print("DEMO 1: User Registration and Login")
    print("="*60)
    
    client = SecureAPIClient()
    
    try:
        # Register a new user
        print("\n1. Registering new user...")
        user = await client.register(
            username="john_doe",
            email="john@example.com",
            password="SecurePass123",
            full_name="John Doe"
        )
        print(f"✓ Registered user: {user['username']} (ID: {user['id']})")
        print(f"  Email: {user['email']}")
        print(f"  Roles: {user['roles']}")
        
        # Login
        print("\n2. Logging in...")
        token_data = await client.login("john_doe", "SecurePass123")
        
        # Get user info
        print("\n3. Getting user info...")
        me = await client.get_me()
        print(f"✓ Current user: {me['username']}")
        print(f"  Email: {me['email']}")
        print(f"  Roles: {me['roles']}")
        print(f"  Scopes: {me['scopes']}")
        
    except httpx.HTTPStatusError as e:
        print(f"✗ Error: {e.response.status_code} - {e.response.text}")
    finally:
        await client.close()


async def demo_authenticated_operations():
    """Demo: Authenticated CRUD operations"""
    print("\n" + "="*60)
    print("DEMO 2: Authenticated Operations")
    print("="*60)
    
    client = SecureAPIClient()
    
    try:
        # Login as admin
        print("\n1. Logging in as admin...")
        await client.login("admin", "admin123")
        
        # Create a product
        print("\n2. Creating a product...")
        product = await client.create_product({
            "name": "Smart Watch Ultra",
            "description": "Advanced fitness tracker with heart rate monitoring",
            "price": 399.99,
            "category": "Electronics",
            "tags": ["wearable", "fitness", "smartwatch"]
        })
        print(f"✓ Created product: {product['name']} (ID: {product['id']})")
        
        # List products
        print("\n3. Listing products...")
        products = await client.get_products(limit=5)
        print(f"✓ Found {len(products)} products")
        for p in products:
            print(f"  - {p['name']}: ${p['price']}")
        
        # Search products
        print("\n4. Searching products...")
        results = await client.search_products(text="fitness tracker")
        print(f"✓ Found {len(results)} results")
        for result in results[:3]:
            entity = result['entity']
            score = result['score']
            print(f"  - {entity['name']} (score: {score:.3f})")
        
    except httpx.HTTPStatusError as e:
        print(f"✗ Error: {e.response.status_code} - {e.response.text}")
    finally:
        await client.close()


async def demo_public_vs_authenticated():
    """Demo: Public vs authenticated access"""
    print("\n" + "="*60)
    print("DEMO 3: Public vs Authenticated Access")
    print("="*60)
    
    client = SecureAPIClient()
    
    try:
        # Try to access products without authentication
        print("\n1. Trying to access products without auth...")
        try:
            products = await client.get_products()
            print(f"✓ Got {len(products)} products")
        except httpx.HTTPStatusError as e:
            print(f"✗ Access denied: {e.response.status_code}")
            print(f"  Message: {e.response.json()['detail']}")
        
        # Access public reviews without authentication
        print("\n2. Accessing public reviews (no auth)...")
        reviews = await client.get_reviews(limit=5, authenticated=False)
        print(f"✓ Got {len(reviews)} reviews (public access)")
        
        # Login
        print("\n3. Logging in...")
        await client.login("admin", "admin123")
        
        # Now access products with authentication
        print("\n4. Accessing products with auth...")
        products = await client.get_products()
        print(f"✓ Got {len(products)} products (authenticated access)")
        
    except httpx.HTTPStatusError as e:
        print(f"✗ Error: {e.response.status_code} - {e.response.text}")
    finally:
        await client.close()


async def demo_permission_errors():
    """Demo: Permission denied scenarios"""
    print("\n" + "="*60)
    print("DEMO 4: Permission Denied Scenarios")
    print("="*60)
    
    client = SecureAPIClient()
    
    try:
        # Register regular user
        print("\n1. Registering regular user...")
        try:
            await client.register(
                username="regular_user",
                email="regular@example.com",
                password="password123"
            )
        except httpx.HTTPStatusError:
            pass  # User might already exist
        
        # Login as regular user
        print("\n2. Logging in as regular user...")
        await client.login("regular_user", "password123")
        
        # Try to access admin dashboard
        print("\n3. Trying to access admin dashboard...")
        try:
            dashboard = await client.admin_dashboard()
            print(f"✓ Accessed dashboard: {dashboard}")
        except httpx.HTTPStatusError as e:
            print(f"✗ Access denied: {e.response.status_code}")
            print(f"  Message: {e.response.json()['detail']}")
        
        # Try to list all users
        print("\n4. Trying to list all users...")
        try:
            users = await client.list_users()
            print(f"✓ Listed {len(users)} users")
        except httpx.HTTPStatusError as e:
            print(f"✗ Access denied: {e.response.status_code}")
            print(f"  Message: {e.response.json()['detail']}")
        
        # Login as admin
        print("\n5. Logging in as admin...")
        await client.login("admin", "admin123")
        
        # Now access admin dashboard
        print("\n6. Accessing admin dashboard as admin...")
        dashboard = await client.admin_dashboard()
        print(f"✓ Dashboard data:")
        print(f"  User: {dashboard['user']}")
        print(f"  Roles: {dashboard['role']}")
        print(f"  Total users: {dashboard['total_users']}")
        
    except httpx.HTTPStatusError as e:
        print(f"✗ Error: {e.response.status_code} - {e.response.text}")
    finally:
        await client.close()


async def demo_password_change():
    """Demo: Password change"""
    print("\n" + "="*60)
    print("DEMO 5: Password Change")
    print("="*60)
    
    client = SecureAPIClient()
    
    try:
        # Register user
        print("\n1. Registering user...")
        try:
            await client.register(
                username="test_user",
                email="test@example.com",
                password="OldPassword123"
            )
        except httpx.HTTPStatusError:
            pass  # User might already exist
        
        # Login
        print("\n2. Logging in with old password...")
        await client.login("test_user", "OldPassword123")
        
        # Change password
        print("\n3. Changing password...")
        result = await client.change_password("OldPassword123", "NewPassword123")
        print(f"✓ {result['message']}")
        
        # Try logging in with old password (should fail)
        print("\n4. Trying to login with old password...")
        client2 = SecureAPIClient()
        try:
            await client2.login("test_user", "OldPassword123")
            print("✗ Should have failed!")
        except httpx.HTTPStatusError as e:
            print(f"✓ Login failed as expected: {e.response.status_code}")
        
        # Login with new password
        print("\n5. Logging in with new password...")
        await client2.login("test_user", "NewPassword123")
        print("✓ Login successful with new password")
        
        await client2.close()
        
    except httpx.HTTPStatusError as e:
        print(f"✗ Error: {e.response.status_code} - {e.response.text}")
    finally:
        await client.close()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Secure API Client Demos                                  ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Make sure the API is running at http://localhost:8000
    
    Run: python secure_example.py
    """)
    
    print("\nChoose a demo:")
    print("1. User registration and login")
    print("2. Authenticated operations")
    print("3. Public vs authenticated access")
    print("4. Permission denied scenarios")
    print("5. Password change")
    print("6. Run all demos")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == "1":
        asyncio.run(demo_user_registration_and_login())
    elif choice == "2":
        asyncio.run(demo_authenticated_operations())
    elif choice == "3":
        asyncio.run(demo_public_vs_authenticated())
    elif choice == "4":
        asyncio.run(demo_permission_errors())
    elif choice == "5":
        asyncio.run(demo_password_change())
    elif choice == "6":
        async def run_all():
            await demo_user_registration_and_login()
            await demo_authenticated_operations()
            await demo_public_vs_authenticated()
            await demo_permission_errors()
            await demo_password_change()
        
        asyncio.run(run_all())
    else:
        print("Invalid choice")
