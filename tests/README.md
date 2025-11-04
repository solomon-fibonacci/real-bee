# real-bee Test Suite

Comprehensive testing for the real-bee framework.

## Running Tests

### Prerequisites

1. Start test services:
```bash
docker-compose -f docker-compose.test.yml up -d
```

2. Install test dependencies:
```bash
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=realbee --cov-report=html

# Run with verbose output
pytest -v
```

### Run Specific Test Suites

```bash
# Unit tests only (fast, no external dependencies)
pytest tests/unit -m unit

# Integration tests (requires docker services)
pytest tests/integration -m integration

# End-to-end tests
pytest tests/e2e -m e2e

# Performance tests
pytest tests/performance -m performance
```

### Run Specific Test Files

```bash
# Single test file
pytest tests/unit/test_utils.py

# Specific test class
pytest tests/unit/test_utils.py::TestToSnakeCase

# Specific test method
pytest tests/unit/test_utils.py::TestToSnakeCase::test_simple_camel_case
```

### Run Tests in Parallel

```bash
# Run tests across 4 CPU cores
pytest -n 4
```

## Test Organization

```
tests/
├── unit/                    # Unit tests (fast, mocked dependencies)
│   ├── test_utils.py
│   ├── test_models.py
│   ├── test_core.py
│   ├── test_database_unit.py
│   ├── test_cache_unit.py
│   ├── test_events_unit.py
│   ├── test_search_unit.py
│   ├── test_websocket_unit.py
│   └── test_routes_unit.py
│
├── integration/             # Integration tests (real services)
│   ├── test_database_integration.py
│   ├── test_cache_integration.py
│   ├── test_events_integration.py
│   ├── test_search_integration.py
│   └── test_framework_integration.py
│
├── e2e/                     # End-to-end tests (complete workflows)
│   ├── test_crud_workflows.py
│   ├── test_realtime_updates.py
│   ├── test_search_workflows.py
│   └── test_error_recovery.py
│
├── performance/             # Performance benchmarks
│   ├── test_latency.py
│   ├── test_throughput.py
│   └── test_memory.py
│
├── load/                    # Load and stress tests
│   ├── test_concurrent_operations.py
│   └── test_websocket_load.py
│
├── chaos/                   # Chaos/failure tests
│   ├── test_database_failures.py
│   └── test_redis_failures.py
│
├── conftest.py             # Shared fixtures
├── mocks.py                # Mock objects
├── factories.py            # Test data factories
└── README.md               # This file
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.asyncio` - Async tests

## Writing Tests

### Test Structure

Use the Arrange-Act-Assert (AAA) pattern:

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

### Using Fixtures

```python
async def test_with_database(clean_db):
    """Test using clean database fixture"""
    # clean_db is automatically cleaned after test
    pass

async def test_with_framework(framework):
    """Test using configured framework"""
    # Framework is ready to use
    pass
```

### Using Factories

```python
def test_with_test_data():
    # Single product
    product = ProductFactory.build()

    # Multiple products
    products = ProductFactory.build_batch(10)

    # Custom fields
    product = ProductFactory.build(name="Custom Name", price=99.99)
```

## Coverage Requirements

- **Overall**: Minimum 90% line coverage
- **Critical paths**: 100% coverage (CRUD, events, WebSocket)
- **Error handling**: 100% coverage

Check coverage:
```bash
pytest --cov=realbee --cov-report=term-missing

# Fail if coverage < 90%
pytest --cov=realbee --cov-fail-under=90
```

## Continuous Integration

Tests run automatically on:
- Every push to any branch
- Every pull request
- Python versions: 3.9, 3.10, 3.11, 3.12

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Tests fail with "connection refused"

Make sure test services are running:
```bash
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml ps
```

### Tests are slow

Run only unit tests:
```bash
pytest tests/unit
```

Or run tests in parallel:
```bash
pytest -n auto
```

### Database tests fail

Clean and restart PostgreSQL:
```bash
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

### Redis tests fail

Restart Redis:
```bash
docker-compose -f docker-compose.test.yml restart redis-test
```

## Best Practices

1. **Keep tests isolated** - Each test should be independent
2. **Use fixtures** - Avoid duplicating setup code
3. **Use factories** - Generate test data with factories
4. **Test edge cases** - Don't just test happy paths
5. **Mock external services** - Use mocks for unit tests
6. **Clear test names** - Use descriptive test function names
7. **Fast unit tests** - Unit tests should run in <1ms each
8. **Clean up after tests** - Use fixtures that auto-cleanup

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Strategy](../TESTING_STRATEGY.md)
- [Contributing Guide](../CONTRIBUTING.md) (when available)
