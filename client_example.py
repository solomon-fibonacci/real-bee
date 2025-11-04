"""
Client Example: Using the real-time WebSocket API
"""
import asyncio
import json
from datetime import datetime
import websockets
import httpx


class RealtimeClient:
    """Client for interacting with the real-time API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.client = httpx.AsyncClient(base_url=base_url)
        self.ws = None
    
    async def connect_websocket(self, entity_type: str):
        """Connect to WebSocket for real-time updates"""
        ws_endpoint = f"{self.ws_url}/ws/{entity_type}"
        self.ws = await websockets.connect(ws_endpoint)
        print(f"Connected to WebSocket: {ws_endpoint}")
    
    async def listen_for_updates(self):
        """Listen for real-time updates"""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
        
        async for message in self.ws:
            data = json.loads(message)
            print(f"\n[{datetime.now()}] Received update:")
            print(json.dumps(data, indent=2))
    
    async def send_ping(self):
        """Send periodic pings to keep connection alive"""
        while self.ws:
            await asyncio.sleep(30)
            await self.ws.send(json.dumps({"type": "ping"}))
    
    # REST API methods
    async def create_product(self, product_data: dict):
        """Create a new product"""
        response = await self.client.post("/products", json=product_data)
        response.raise_for_status()
        return response.json()
    
    async def get_products(self, limit: int = 10):
        """Get list of products"""
        response = await self.client.get("/products", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    
    async def update_product(self, product_id: int, updates: dict):
        """Update a product"""
        response = await self.client.patch(f"/products/{product_id}", json=updates)
        response.raise_for_status()
        return response.json()
    
    async def delete_product(self, product_id: int):
        """Delete a product"""
        response = await self.client.delete(f"/products/{product_id}")
        response.raise_for_status()
        return response.json()
    
    async def search_products(self, text: str = None, image_url: str = None, k: int = 10):
        """Multimodal search for products"""
        params = {"k": k}
        if text:
            params["text"] = text
        if image_url:
            params["image_url"] = image_url
        
        response = await self.client.post("/products/search", params=params)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close connections"""
        if self.ws:
            await self.ws.close()
        await self.client.aclose()


async def demo_realtime_updates():
    """Demo: Real-time updates with WebSocket"""
    client = RealtimeClient()
    
    try:
        # Connect to WebSocket for products
        await client.connect_websocket("products")
        
        # Start listening for updates in background
        listen_task = asyncio.create_task(client.listen_for_updates())
        ping_task = asyncio.create_task(client.send_ping())
        
        # Wait a bit for connection to establish
        await asyncio.sleep(1)
        
        # Create a product (this will trigger a real-time update)
        print("\n=== Creating product ===")
        product = await client.create_product({
            "name": "Smart Watch Pro",
            "description": "Advanced fitness tracking with heart rate monitor",
            "price": 299.99,
            "category": "Electronics",
            "tags": ["fitness", "wearable", "smartwatch"]
        })
        print(f"Created product: {product['id']}")
        
        await asyncio.sleep(2)
        
        # Update the product (this will also trigger an update)
        print("\n=== Updating product ===")
        await client.update_product(product['id'], {
            "price": 279.99,
            "description": "Advanced fitness tracking with heart rate monitor - NOW ON SALE!"
        })
        
        await asyncio.sleep(2)
        
        # Delete the product (another update)
        print("\n=== Deleting product ===")
        await client.delete_product(product['id'])
        
        # Keep listening for a bit
        await asyncio.sleep(2)
        
        # Cancel tasks
        listen_task.cancel()
        ping_task.cancel()
        
    finally:
        await client.close()


async def demo_multimodal_search():
    """Demo: Multimodal search"""
    client = RealtimeClient()
    
    try:
        # Create some products
        print("\n=== Creating products for search ===")
        products = [
            {
                "name": "Running Shoes",
                "description": "Comfortable running shoes with cushioned sole",
                "price": 89.99,
                "category": "Footwear",
                "tags": ["running", "shoes", "sports"]
            },
            {
                "name": "Yoga Mat",
                "description": "Non-slip yoga mat for all types of exercise",
                "price": 29.99,
                "category": "Fitness",
                "tags": ["yoga", "fitness", "exercise"]
            },
            {
                "name": "Protein Shake",
                "description": "High protein shake for post-workout recovery",
                "price": 39.99,
                "category": "Nutrition",
                "tags": ["protein", "nutrition", "supplement"]
            }
        ]
        
        for product_data in products:
            await client.create_product(product_data)
        
        # Wait for embeddings to be generated
        await asyncio.sleep(3)
        
        # Search by text
        print("\n=== Searching for 'fitness equipment' ===")
        results = await client.search_products(text="fitness equipment", k=5)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            entity = result['entity']
            score = result['score']
            print(f"{i}. {entity['name']} (score: {score:.3f})")
            print(f"   {entity['description']}")
            print(f"   Price: ${entity['price']}")
        
    finally:
        await client.close()


async def demo_bulk_operations():
    """Demo: Bulk operations"""
    client = RealtimeClient()
    
    try:
        print("\n=== Bulk creating products ===")
        
        bulk_products = [
            {
                "name": f"Product {i}",
                "description": f"Description for product {i}",
                "price": 10.0 + i,
                "category": "Test",
                "tags": ["test"]
            }
            for i in range(1, 11)
        ]
        
        # Bulk create (more efficient than creating one-by-one)
        response = await client.client.post("/products/bulk", json=bulk_products)
        response.raise_for_status()
        created = response.json()
        
        print(f"Created {len(created)} products in bulk")
        
        # List all products
        print("\n=== Listing products ===")
        products = await client.get_products(limit=20)
        print(f"Total products: {len(products)}")
        for product in products[:5]:
            print(f"- {product['name']}: ${product['price']}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    print("=== Real-time CRUD Framework Demo ===\n")
    print("Choose a demo:")
    print("1. Real-time updates with WebSocket")
    print("2. Multimodal search")
    print("3. Bulk operations")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(demo_realtime_updates())
    elif choice == "2":
        asyncio.run(demo_multimodal_search())
    elif choice == "3":
        asyncio.run(demo_bulk_operations())
    else:
        print("Invalid choice")
