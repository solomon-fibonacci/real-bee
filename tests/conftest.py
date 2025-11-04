"""
Pytest configuration and shared fixtures for real-bee tests
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime

from fastapi import FastAPI
from httpx import AsyncClient

# Import real-bee components
from realbee import CRUDFramework, FrameworkConfig
from realbee.database import DatabaseManager
from realbee.cache import CacheManager
from realbee.events import EventBus
from realbee.search import SearchEngine
from realbee.websocket import WebSocketManager

# Import mocks and factories
from tests.mocks import MockDatabase, MockRedis, MockClipModel
from tests.factories import ProductFactory, UserFactory, ReviewFactory


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_config() -> FrameworkConfig:
    """Test configuration using test database and Redis"""
    return FrameworkConfig(
        postgres_url="postgresql://test:test@localhost:5433/realbee_test",
        postgres_pool_size=5,
        redis_url="redis://localhost:6380/0",
        redis_pool_size=10,
        cache_enabled=True,
        cache_ttl=60,
        faiss_dimension=512,
        clip_device="cpu",
        ws_heartbeat_interval=30,
        ws_max_connections=100,
        event_history_size=100,
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def db_manager(test_config: FrameworkConfig) -> AsyncGenerator[DatabaseManager, None]:
    """Database manager with test database"""
    db = DatabaseManager(test_config)
    await db.initialize()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def clean_db(db_manager: DatabaseManager) -> AsyncGenerator[DatabaseManager, None]:
    """Database that's cleaned after each test"""
    yield db_manager

    # Cleanup - drop all tables
    async with db_manager.acquire() as conn:
        await conn.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)


@pytest.fixture
def mock_db() -> MockDatabase:
    """Mock database for unit tests"""
    return MockDatabase()


# ============================================================================
# Cache/Redis Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def cache_manager(test_config: FrameworkConfig) -> AsyncGenerator[CacheManager, None]:
    """Cache manager with test Redis"""
    cache = CacheManager(test_config)
    await cache.initialize()
    yield cache
    await cache.close()


@pytest_asyncio.fixture
async def clean_cache(cache_manager: CacheManager) -> AsyncGenerator[CacheManager, None]:
    """Cache that's flushed after each test"""
    yield cache_manager

    # Flush all keys
    if cache_manager.redis:
        await cache_manager.redis.flushdb()


@pytest.fixture
def mock_cache() -> MockRedis:
    """Mock Redis for unit tests"""
    return MockRedis()


# ============================================================================
# Event Bus Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def event_bus(clean_cache: CacheManager) -> AsyncGenerator[EventBus, None]:
    """Event bus with clean cache"""
    bus = EventBus(clean_cache, event_history_size=100)
    await bus.start()
    yield bus
    await bus.stop()


# ============================================================================
# Search Engine Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def search_engine(test_config: FrameworkConfig) -> AsyncGenerator[SearchEngine, None]:
    """Search engine for tests"""
    engine = SearchEngine(test_config)
    await engine.initialize()
    yield engine
    await engine.close()


@pytest.fixture
def mock_clip_model() -> MockClipModel:
    """Mock CLIP model for unit tests"""
    return MockClipModel()


# ============================================================================
# WebSocket Fixtures
# ============================================================================

@pytest.fixture
def ws_manager() -> WebSocketManager:
    """WebSocket manager for tests"""
    return WebSocketManager(heartbeat_interval=5, max_connections=100)


# ============================================================================
# Framework Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def app() -> FastAPI:
    """FastAPI application for tests"""
    return FastAPI(title="Test API")


@pytest_asyncio.fixture
async def framework(
    app: FastAPI,
    test_config: FrameworkConfig,
    clean_db: DatabaseManager,
    clean_cache: CacheManager
) -> AsyncGenerator[CRUDFramework, None]:
    """Fully configured CRUDFramework for integration tests"""
    fw = CRUDFramework(app, test_config)
    await fw.startup()
    yield fw
    await fw.shutdown()


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing API endpoints"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def sample_product():
    """Generate a sample product"""
    return ProductFactory.build()


@pytest.fixture
def sample_products():
    """Generate multiple sample products"""
    return ProductFactory.build_batch(10)


@pytest.fixture
def sample_user():
    """Generate a sample user"""
    return UserFactory.build()


@pytest.fixture
def sample_review():
    """Generate a sample review"""
    return ReviewFactory.build()


# ============================================================================
# Entity Schema Fixtures
# ============================================================================

@pytest.fixture
def product_schema():
    """Product schema for testing"""
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
            vector_fields = ["description"]

    return Product


@pytest.fixture
def user_schema():
    """User schema for testing"""
    from typing import Optional
    from pydantic import BaseModel, Field

    class User(BaseModel):
        id: Optional[int] = None
        email: str = Field(..., description="User email")
        name: str = Field(..., description="User name")

    return User


# ============================================================================
# Async Helpers
# ============================================================================

@pytest.fixture
def wait_for_event():
    """Helper to wait for async events"""
    async def _wait(condition, timeout=5.0, interval=0.1):
        """Wait for condition to become True"""
        elapsed = 0.0
        while elapsed < timeout:
            if await condition() if asyncio.iscoroutinefunction(condition) else condition():
                return True
            await asyncio.sleep(interval)
            elapsed += interval
        return False

    return _wait


# ============================================================================
# Cleanup Hooks
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton state between tests"""
    yield
    # Add cleanup code here if needed


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
