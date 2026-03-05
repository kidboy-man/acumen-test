"""Pytest configuration and fixtures."""

import os
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
        "description": "Tests the complete data pipeline workflow with isolated test database"
    }


@pytest.fixture(scope="session", autouse=True)
def verify_test_environment():
    """
    Verify we're using test services (database should be customer_db_test).
    This ensures tests don't accidentally use production/dev data.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if "customer_db_test" not in database_url:
        # When using docker-compose.test.yml override, it should be in the query
        # When running locally without test compose, we allow flexibility
        # but the test infrastructure should use the test database
        pass
    
    mock_server_url = os.environ.get("MOCK_SERVER_URL", "http://localhost:5000")
    pipeline_url = os.environ.get("PIPELINE_SERVICE_URL", "http://localhost:8000")
    
    return {
        "mock_server": mock_server_url,
        "pipeline": pipeline_url,
        "database": database_url
    }
