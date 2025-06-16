import pytest

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that involve database operations"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )