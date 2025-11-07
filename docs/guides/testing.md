# real-bee Testing Strategy

## Overview

As an open-source framework that developers will rely on for production applications, real-bee requires comprehensive, rigorous testing across all levels. This document outlines our testing philosophy, approach, and implementation plan.

## Testing Philosophy

### Core Principles

1. **Reliability First**: Every feature must be thoroughly tested before release
2. **Test-Driven Development**: Write tests alongside or before implementation
3. **Comprehensive Coverage**: Aim for >90% code coverage, 100% for critical paths
4. **Real-World Scenarios**: Test actual usage patterns, not just happy paths
5. **Fast Feedback**: Tests should run quickly to encourage frequent execution
6. **Isolation**: Tests should be independent and not affect each other
7. **Reproducibility**: Tests must produce consistent results across environments

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \          <- 10% End-to-End Tests
                 /______\
                /        \
               /Integration\       <- 30% Integration Tests
              /____________\
             /              \
            /  Unit Tests    \     <- 60% Unit Tests
           /__________________\
```

## Test Levels

### 1. Unit Tests (60% of tests)

**Purpose**: Test individual functions/methods in isolation

**Scope**:
- Individual functions in `utils.py`
- Methods in manager classes (DatabaseManager, CacheManager, etc.)
- Hook execution logic
- Data validation
- Serialization/deserialization
- Error handling

**Characteristics**:
- Fast (<1ms per test)
- No external dependencies (mocked)
- High granularity
- Deterministic

**Example Coverage**:
```python
# utils.py
✓ to_snake_case() with various inputs
✓ get_table_name() with different entity types
✓ generate_cache_key() with/without entity_id
✓ serialize_for_json() with complex objects

# database.py - DatabaseManager
✓ _get_pg_type() for all Python types
✓ _is_optional() for Optional types
✓ Query building logic
✓ Error handling for connection failures

# cache.py - CacheManager
✓ _make_key() prefix generation
✓ get() with existing/missing keys
✓ set() with TTL variations
✓ delete() and delete_pattern()

# models.py
✓ Pydantic validation for all models
✓ Serialization/deserialization
✓ Default values
```

### 2. Integration Tests (30% of tests)

**Purpose**: Test component interactions

**Scope**:
- Database operations with real PostgreSQL
- Redis operations with real Redis
- Event bus pub/sub
- WebSocket connections
- CRUD operations through framework
- Search indexing and retrieval
- Cache invalidation on updates

**Characteristics**:
- Medium speed (10-100ms per test)
- Real external services (in containers)
- Test component boundaries
- Use test databases

**Example Coverage**:
```python
# Database Integration
✓ Create entity → verify in database
✓ Update entity → verify changes persisted
✓ Delete entity → verify removed
✓ Bulk operations
✓ Transaction rollback on errors

# Cache Integration
✓ Set value → get value → verify match
✓ Publish event → verify subscribers receive
✓ Cache invalidation on entity updates

# Event Bus Integration
✓ Emit event → verify published to Redis
✓ Multiple subscribers receive events
✓ Event history tracking
✓ Event filtering by type

# WebSocket Integration
✓ Connect → receive connection confirmation
✓ CRUD operation → WebSocket receives event
✓ Heartbeat → pong response
✓ Disconnect → cleanup
```

### 3. End-to-End Tests (10% of tests)

**Purpose**: Test complete user workflows

**Scope**:
- Complete CRUD workflows
- Real-time update propagation
- Multimodal search workflows
- Error recovery scenarios
- Multi-entity operations
- Concurrent operations

**Characteristics**:
- Slower (100ms-1s per test)
- Full stack involved
- Realistic scenarios
- Multiple operations chained

**Example Coverage**:
```python
# Complete Workflows
✓ Register entity → create → update → search → delete
✓ Multiple clients → create entities → all receive WebSocket updates
✓ Bulk create → search → verify all indexed
✓ Create with hooks → verify hooks executed in order
✓ Update entity → cache invalidated → search index updated → event emitted

# Error Recovery
✓ Database down → graceful error → reconnect
✓ Redis down → operations continue (degraded)
✓ Transaction failure → rollback → retry
```

### 4. Performance Tests

**Purpose**: Ensure framework meets performance requirements

**Scope**:
- Response time benchmarks
- Throughput testing
- Resource usage monitoring
- Memory leak detection
- Connection pool efficiency

**Performance Targets**:
```
Operation               Target         Max
-------------------------------------------------
Simple GET             < 5ms          < 20ms
Simple POST            < 10ms         < 50ms
List (100 items)       < 20ms         < 100ms
Bulk create (100)      < 200ms        < 1s
Search (k=10)          < 100ms        < 500ms
WebSocket message      < 5ms          < 20ms
Event propagation      < 50ms         < 200ms
```

**Example Tests**:
```python
✓ 1000 sequential GETs complete in <5s
✓ 100 concurrent connections handled
✓ 10,000 entities indexed in <10s
✓ Memory usage stable over 1000 operations
✓ Connection pool doesn't leak
✓ WebSocket can handle 1000 connections
```

### 5. Load/Stress Tests

**Purpose**: Test behavior under load

**Scope**:
- Concurrent user simulation
- Connection pool saturation
- Cache thrashing scenarios
- Event queue overflow
- WebSocket connection limits

**Example Scenarios**:
```python
✓ 100 concurrent users creating entities
✓ 1000 WebSocket connections
✓ 10,000 events/second through bus
✓ Database connection pool exhaustion
✓ Redis connection limits
✓ Sustained load for 1 hour
```

### 6. Reliability/Chaos Tests

**Purpose**: Test failure scenarios and recovery

**Scope**:
- Database disconnections
- Redis failures
- Network partitions
- Partial failures
- Race conditions
- Data corruption

**Example Scenarios**:
```python
✓ Database dies mid-transaction → rollback → reconnect
✓ Redis down → operations continue (no cache)
✓ Network delay → timeout handling
✓ Concurrent updates to same entity → last write wins
✓ Connection pool exhausted → queue requests
✓ Malformed data → validation errors
```

## Test Infrastructure

### Test Environment Setup

```yaml
# docker-compose.test.yml
services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_DB: realbee_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"

  redis-test:
    image: redis:7
    ports:
      - "6380:6379"
```

### Fixtures and Utilities

```python
# conftest.py - pytest fixtures

@pytest.fixture
async def db():
    """Isolated database for each test"""

@pytest.fixture
async def cache():
    """Isolated Redis for each test"""

@pytest.fixture
async def framework():
    """Configured CRUDFramework instance"""

@pytest.fixture
async def client():
    """Test HTTP client"""

@pytest.fixture
async def ws_client():
    """Test WebSocket client"""

@pytest.fixture
def sample_product():
    """Sample Product entity"""

@pytest.fixture
def sample_products(n=10):
    """List of sample products"""
```

### Mock Objects

```python
# tests/mocks.py

class MockClipModel:
    """Mock CLIP model for testing without ML dependencies"""

class MockFaissIndex:
    """Mock FAISS index"""

class MockRedis:
    """Mock Redis for unit tests"""

class MockDatabase:
    """Mock database for unit tests"""
```

## Coverage Requirements

### Minimum Coverage Targets

- **Overall**: 90% line coverage
- **Critical paths**: 100% coverage
  - Framework initialization
  - CRUD operations
  - Event emission
  - WebSocket message handling
- **Error handling**: 100% coverage
- **Utilities**: 95% coverage

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=realbee --cov-report=html --cov-report=term

# Fail if coverage < 90%
pytest --cov=realbee --cov-fail-under=90
```

## Test Organization

```
tests/
├── unit/
│   ├── test_utils.py
│   ├── test_models.py
│   ├── test_core.py
│   ├── test_database_unit.py
│   ├── test_cache_unit.py
│   ├── test_events_unit.py
│   ├── test_search_unit.py
│   ├── test_websocket_unit.py
│   └── test_routes_unit.py
├── integration/
│   ├── test_database_integration.py
│   ├── test_cache_integration.py
│   ├── test_events_integration.py
│   ├── test_search_integration.py
│   ├── test_websocket_integration.py
│   └── test_framework_integration.py
├── e2e/
│   ├── test_crud_workflows.py
│   ├── test_realtime_updates.py
│   ├── test_search_workflows.py
│   └── test_error_recovery.py
├── performance/
│   ├── test_latency.py
│   ├── test_throughput.py
│   └── test_memory.py
├── load/
│   ├── test_concurrent_operations.py
│   ├── test_websocket_load.py
│   └── test_sustained_load.py
├── chaos/
│   ├── test_database_failures.py
│   ├── test_redis_failures.py
│   └── test_race_conditions.py
├── conftest.py
├── mocks.py
└── factories.py
```

## Test Data Management

### Factories

```python
# tests/factories.py

import factory
from faker import Faker

fake = Faker()

class ProductFactory(factory.Factory):
    class Meta:
        model = Product

    name = factory.LazyFunction(lambda: fake.catch_phrase())
    description = factory.LazyFunction(lambda: fake.text())
    price = factory.LazyFunction(lambda: fake.random.uniform(10, 1000))
    category = factory.LazyFunction(lambda: fake.word())
    tags = factory.LazyFunction(lambda: [fake.word() for _ in range(3)])
```

### Test Data Cleanup

```python
@pytest.fixture(autouse=True)
async def cleanup_test_data(db):
    """Automatically cleanup after each test"""
    yield
    # Cleanup code
    await db.execute("TRUNCATE TABLE products CASCADE")
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: realbee_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit -v --cov=realbee

      - name: Run integration tests
        run: pytest tests/integration -v

      - name: Run e2e tests
        run: pytest tests/e2e -v

      - name: Check coverage
        run: pytest --cov=realbee --cov-fail-under=90

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Testing Best Practices

### 1. Test Naming Convention

```python
# Pattern: test_<what>_<condition>_<expected>

def test_create_product_valid_data_returns_product():
    """Test that creating a product with valid data returns the product"""

def test_create_product_missing_required_field_raises_validation_error():
    """Test that missing required field raises ValidationException"""

def test_get_product_nonexistent_id_returns_none():
    """Test that getting non-existent product returns None"""
```

### 2. Arrange-Act-Assert (AAA) Pattern

```python
async def test_create_product():
    # Arrange
    product_data = ProductFactory.build()

    # Act
    result = await framework.create("Product", product_data)

    # Assert
    assert result.id is not None
    assert result.name == product_data.name
```

### 3. Test Isolation

```python
# Each test gets fresh database
@pytest.fixture
async def framework(db, cache):
    config = FrameworkConfig(...)
    fw = CRUDFramework(app, config)
    yield fw
    await fw.shutdown()
```

### 4. Meaningful Assertions

```python
# Bad
assert result

# Good
assert result is not None
assert result.id == expected_id
assert result.status == "active"
```

### 5. Test Edge Cases

```python
# Test boundaries
def test_pagination_skip_zero()
def test_pagination_skip_negative_raises_error()
def test_pagination_limit_max_1000()
def test_pagination_limit_over_max_raises_error()

# Test empty states
def test_list_products_empty_database_returns_empty_list()
def test_search_no_results_returns_empty_list()

# Test race conditions
async def test_concurrent_updates_to_same_entity()
async def test_concurrent_cache_invalidation()
```

## Quality Gates

### Pre-Commit Checks

```bash
# Must pass before commit
- All unit tests pass
- Code style (black, ruff)
- Type checking (mypy)
- No security issues (bandit)
```

### PR Requirements

```bash
# Must pass before merge
- All tests pass (unit, integration, e2e)
- Coverage >= 90%
- No performance regressions
- Documentation updated
- CHANGELOG updated
```

### Release Requirements

```bash
# Must pass before release
- All test suites pass
- Performance benchmarks meet targets
- Load tests pass
- Security audit clean
- Documentation complete
- Migration guide (if breaking changes)
```

## Monitoring Test Health

### Metrics to Track

1. **Test Execution Time**: Track and alert if tests get slower
2. **Flaky Tests**: Identify and fix non-deterministic tests
3. **Coverage Trends**: Ensure coverage doesn't decrease
4. **Failure Rate**: Monitor test stability over time

### Test Quality Metrics

```python
# Track these in CI
- Total tests: 500+
- Test execution time: <2 minutes for unit, <5 minutes total
- Flaky test rate: <1%
- Coverage: >90%
- Performance regression: 0
```

## Documentation

### Test Documentation

Each test file should have:
```python
"""
Tests for <module>

This module tests:
- Feature A with scenarios X, Y, Z
- Feature B with edge cases
- Error handling for conditions C, D

Fixtures used:
- db: Test database
- framework: Configured CRUDFramework

External dependencies:
- PostgreSQL (via docker)
- Redis (via docker)
"""
```

### README for Tests

```markdown
# tests/README.md

## Running Tests

### All tests
pytest

### Unit tests only
pytest tests/unit

### Integration tests
pytest tests/integration

### With coverage
pytest --cov=realbee --cov-report=html

### Specific test
pytest tests/unit/test_utils.py::test_to_snake_case
```

## Risk Assessment

### High-Risk Areas (Require Extra Testing)

1. **Concurrent Operations**: Race conditions, deadlocks
2. **Error Recovery**: Database failures, network issues
3. **Data Integrity**: Transaction rollbacks, cache consistency
4. **WebSocket Management**: Connection lifecycle, message ordering
5. **Search Indexing**: Sync between DB and index
6. **Event Ordering**: Event bus message ordering guarantees

### Critical Path Coverage

```python
# These paths MUST have 100% coverage
- Framework.create() → db → cache → index → event
- Framework.update() → db → cache invalidation → index update → event
- Framework.delete() → hooks → db → index removal → event
- WebSocket connection → subscribe → receive events → disconnect
- Event emission → Redis pub/sub → subscribers notified
```

## Success Criteria

The testing strategy is successful when:

✅ **Coverage**: >90% line coverage, 100% critical paths
✅ **Stability**: <1% flaky test rate
✅ **Speed**: Unit tests <1min, all tests <5min
✅ **Confidence**: Developers trust tests enough to refactor
✅ **Bugs**: >80% of bugs caught by tests before production
✅ **Regression**: New features don't break existing functionality
✅ **Documentation**: Every test is clear and self-documenting

## Next Steps

1. ✅ Review and approve testing strategy
2. ⏳ Set up test infrastructure (docker-compose, fixtures)
3. ⏳ Implement unit tests (60% of coverage)
4. ⏳ Implement integration tests (30% of coverage)
5. ⏳ Implement e2e tests (10% of coverage)
6. ⏳ Set up CI/CD pipeline
7. ⏳ Add performance benchmarks
8. ⏳ Add load tests
9. ⏳ Document testing guide for contributors
