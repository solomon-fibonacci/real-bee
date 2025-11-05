# GitHub Actions Workflows

This directory contains CI/CD workflows for the real-bee framework.

## Workflows

### 1. Full Test Suite (`test.yml`)

**Triggers:**
- Push to `main`, `develop`, or `claude/**` branches
- Pull requests to `main` or `develop`

**What it does:**
- Runs on Python 3.9, 3.10, 3.11, 3.12
- Starts PostgreSQL and Redis services
- Runs all tests:
  - Unit tests (175 tests, ~5 seconds)
  - Integration tests (79 tests, ~30 seconds)
  - E2E tests (49 tests, ~60 seconds)
- Checks code quality (ruff, black, mypy)
- Runs security scans (bandit, safety)
- Generates coverage reports
- Uploads to Codecov
- Fails if coverage < 80%

**Duration:** ~5-10 minutes per Python version

### 2. Quick Test (`quick-test.yml`)

**Triggers:**
- Push to any branch
- Pull requests to `main` or `develop`

**What it does:**
- Runs on Python 3.11 only
- Runs unit tests only (fast)
- Basic linting checks

**Duration:** ~30 seconds

## Test Jobs

### Main Test Job
```yaml
jobs:
  test:
    - Unit tests (175 tests)
    - Integration tests (79 tests)
    - E2E tests (49 tests)
    - Coverage reporting
```

### Lint Job
```yaml
jobs:
  lint:
    - ruff (linter)
    - black (formatter)
    - mypy (type checker)
```

### Security Job
```yaml
jobs:
  security:
    - bandit (security scanner)
    - safety (dependency checker)
```

## Services

### PostgreSQL
```yaml
postgres:
  image: postgres:15-alpine
  port: 5433
  credentials:
    user: test
    password: test
    database: realbee_test
```

### Redis
```yaml
redis:
  image: redis:7-alpine
  port: 6380
```

## Coverage

- **Minimum threshold:** 80%
- **Target:** 90%+
- **Reports:**
  - Terminal output
  - XML for Codecov
  - HTML artifacts (downloadable)

## Badges

Add to README.md:

```markdown
![Tests](https://github.com/solomon-fibonacci/real-bee/workflows/Full%20Test%20Suite/badge.svg)
![Coverage](https://codecov.io/gh/solomon-fibonacci/real-bee/branch/main/graph/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
```

## Local Testing

Before pushing, run locally:

```bash
# Quick check (unit tests only)
pytest tests/unit -v

# Full test suite (requires Docker services)
docker-compose -f docker-compose.test.yml up -d
pytest

# With coverage
pytest --cov=realbee --cov-report=html
```

## Debugging Failed Tests

### View logs
1. Go to Actions tab in GitHub
2. Click on failed workflow
3. Click on failed job
4. Expand the failed step

### Common issues

**Services not ready:**
```bash
# Workflow waits up to 30 seconds for services
# If failing, check service health checks
```

**Test timeout:**
```bash
# Increase timeout in pytest.ini
# Or mark slow tests: @pytest.mark.slow
```

**Coverage threshold:**
```bash
# Check coverage report
# Add tests or adjust threshold
```

## Performance

### Execution Times
- Unit tests: ~5 seconds
- Integration tests: ~30 seconds
- E2E tests: ~60 seconds
- **Total per Python version: ~2 minutes**
- **Total for all versions: ~8-10 minutes**

### Optimization
- Tests run in parallel where possible
- Unit tests use mocks (no services needed)
- Integration/E2E share service startup
- Caching for pip dependencies

## Status Checks

For pull requests, these must pass:
- ✅ All tests pass (308 tests)
- ✅ Coverage ≥ 80%
- ✅ No linting errors
- ✅ No security issues (critical)

## Updating Workflows

When updating workflows:

1. Test locally first
2. Update workflow file
3. Commit and push
4. Check Actions tab for results
5. Review logs if failed

## Artifacts

The workflow uploads:
- Coverage HTML report (Python 3.11 only)
- Download from Actions → Workflow Run → Artifacts
