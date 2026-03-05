"""Pytest configuration and fixtures."""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


@pytest.fixture(scope="session")
def test_session_info():
    """Provide test session information."""
    return {
        "name": "Customer Pipeline Integration Tests",
        "description": "Tests the complete data pipeline workflow"
    }
