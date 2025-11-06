"""
Smoke test to verify pytest and package installation works
"""


def test_package_imports():
    """Verify real-bee package can be imported"""
    import realbee
    assert hasattr(realbee, '__version__')
    assert realbee.__version__ == "0.1.0"


def test_core_components_available():
    """Verify core components are importable"""
    from realbee import (
        CRUDFramework,
        FrameworkConfig,
        EntityHooks,
        Event,
        EventType,
    )
    assert CRUDFramework is not None
    assert FrameworkConfig is not None
    assert EntityHooks is not None
    assert Event is not None
    assert EventType is not None


def test_basic_config_creation():
    """Verify FrameworkConfig can be instantiated"""
    from realbee import FrameworkConfig

    config = FrameworkConfig()
    assert config.postgres_url is not None
    assert config.redis_url is not None
    assert config.cache_enabled is True
