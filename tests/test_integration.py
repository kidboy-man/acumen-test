"""
Integration tests for the customer data pipeline.

Tests the complete workflow:
1. Mock Server (Flask) API endpoints
2. Pipeline Service (FastAPI) ingestion
3. Pipeline Service database queries

**Note**: Tests use an isolated test database (customer_db_test) to avoid
polluting production/development data. The test database is automatically
cleaned up after each test run when using `make test`.
"""

import os
import time
import httpx
import pytest


MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://localhost:5000")
PIPELINE_SERVICE_URL = os.environ.get("PIPELINE_SERVICE_URL", "http://localhost:8000")
MAX_RETRIES = 5
RETRY_DELAY = 1


@pytest.fixture
def mock_server_client():
    """Create HTTP client for mock server."""
    return httpx.Client(base_url=MOCK_SERVER_URL, timeout=30.0)


@pytest.fixture
def pipeline_client():
    """Create HTTP client for pipeline service."""
    return httpx.Client(base_url=PIPELINE_SERVICE_URL, timeout=30.0)


def wait_for_service(url: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Wait for a service to be ready by polling it.
    
    Args:
        url: Service URL to check
        max_retries: Maximum number of retry attempts
    
    Returns:
        True if service is ready, False otherwise
    """
    for attempt in range(max_retries):
        try:
            response = httpx.get(f"{url}/api/health", timeout=5.0)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return False


# =====================================================================
# Mock Server Tests
# =====================================================================

class TestMockServer:
    """Test the Flask mock server endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Wait for mock server to be ready before each test."""
        assert wait_for_service(MOCK_SERVER_URL), f"Mock server not available at {MOCK_SERVER_URL}"
    
    def test_health_check(self, mock_server_client):
        """Test mock server health endpoint."""
        response = mock_server_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_list_customers_default_pagination(self, mock_server_client):
        """Test customers endpoint with default pagination."""
        response = mock_server_client.get("/api/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
    
    def test_list_customers_custom_pagination(self, mock_server_client):
        """Test customers endpoint with custom page and limit."""
        response = mock_server_client.get("/api/customers", params={"page": 1, "limit": 5})
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["data"]) <= 5
    
    def test_customer_data_structure(self, mock_server_client):
        """Test that customer objects have required fields."""
        response = mock_server_client.get("/api/customers", params={"limit": 1})
        assert response.status_code == 200
        
        customer = response.json()["data"][0]
        required_fields = [
            "customer_id", "first_name", "last_name", "email",
            "phone", "address", "date_of_birth", "account_balance", "created_at"
        ]
        for field in required_fields:
            assert field in customer, f"Missing field: {field}"


# =====================================================================
# Pipeline Service Tests - Ingestion
# =====================================================================

class TestPipelineIngestion:
    """Test the pipeline service data ingestion."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Wait for services to be ready before each test."""
        assert wait_for_service(PIPELINE_SERVICE_URL), \
            f"Pipeline service not available at {PIPELINE_SERVICE_URL}"
        assert wait_for_service(MOCK_SERVER_URL), \
            f"Mock server not available at {MOCK_SERVER_URL}"
    
    def test_ingest_data(self, pipeline_client):
        """Test data ingestion from mock server into database."""
        response = pipeline_client.post("/api/ingest")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "records_processed" in data
        assert data["records_processed"] > 0
        
        print(f"✓ Successfully ingested {data['records_processed']} records")


# =====================================================================
# Pipeline Service Tests - Database Queries
# =====================================================================

class TestPipelineQueries:
    """Test the pipeline service database query endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self, pipeline_client):
        """Setup: ingest data before running tests."""
        # Wait for service
        assert wait_for_service(PIPELINE_SERVICE_URL), \
            f"Pipeline service not available at {PIPELINE_SERVICE_URL}"
        
        # Ensure data is ingested
        response = pipeline_client.post("/api/ingest")
        assert response.status_code == 200
    
    def test_list_customers_from_database(self, pipeline_client):
        """Test retrieving paginated customers from database."""
        response = pipeline_client.get("/api/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["data"], list)
        assert data["total"] > 0
        
        print(f"✓ Retrieved {data['total']} customers from database")
    
    def test_list_customers_pagination(self, pipeline_client):
        """Test pagination parameters."""
        response = pipeline_client.get("/api/customers", params={"page": 1, "limit": 5})
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["data"]) <= 5
    
    def test_customer_by_id(self, pipeline_client):
        """Test retrieving a single customer by ID."""
        # First, get a customer ID from the list
        response = pipeline_client.get("/api/customers", params={"limit": 1})
        assert response.status_code == 200
        customer_id = response.json()["data"][0]["customer_id"]
        
        # Now fetch that specific customer
        response = pipeline_client.get(f"/api/customers/{customer_id}")
        assert response.status_code == 200
        
        customer = response.json()
        assert customer["customer_id"] == customer_id
        assert "first_name" in customer
        assert "email" in customer
        
        print(f"✓ Retrieved customer {customer_id}: {customer['first_name']} {customer['last_name']}")
    
    def test_customer_not_found(self, pipeline_client):
        """Test retrieving non-existent customer returns 404."""
        response = pipeline_client.get("/api/customers/nonexistent_id")
        assert response.status_code == 404
    
    def test_customer_data_types(self, pipeline_client):
        """Test that customer data has correct types."""
        response = pipeline_client.get("/api/customers", params={"limit": 1})
        assert response.status_code == 200
        
        customer = response.json()["data"][0]
        
        assert isinstance(customer["customer_id"], str)
        assert isinstance(customer["first_name"], str)
        assert isinstance(customer["last_name"], str)
        assert isinstance(customer["email"], str)
        assert isinstance(customer["phone"], (str, type(None)))
        assert isinstance(customer["address"], (str, type(None)))
        assert isinstance(customer["date_of_birth"], (str, type(None)))
        assert isinstance(customer["account_balance"], (float, int, type(None)))
        assert isinstance(customer["created_at"], (str, type(None)))


# =====================================================================
# End-to-End Tests
# =====================================================================

class TestEndToEnd:
    """Test the complete pipeline workflow."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Wait for all services."""
        assert wait_for_service(PIPELINE_SERVICE_URL)
        assert wait_for_service(MOCK_SERVER_URL)
    
    def test_complete_workflow(self, mock_server_client, pipeline_client):
        """
        Test the complete data pipeline workflow:
        1. Fetch data from mock server
        2. Ingest into pipeline
        3. Query from pipeline database
        """
        # Step 1: Get customers from mock server
        mock_response = mock_server_client.get("/api/customers", params={"limit": 5})
        assert mock_response.status_code == 200
        mock_customers = mock_response.json()["data"]
        mock_customer_ids = [c["customer_id"] for c in mock_customers]
        
        print(f"✓ Step 1: Fetched {len(mock_customers)} customers from mock server")
        
        # Step 2: Ingest data
        ingest_response = pipeline_client.post("/api/ingest")
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] == "success"
        
        print(f"✓ Step 2: Ingested {ingest_response.json()['records_processed']} records")
        
        # Step 3: Query from pipeline database
        pipeline_response = pipeline_client.get("/api/customers", params={"limit": 5})
        assert pipeline_response.status_code == 200
        pipeline_customers = pipeline_response.json()["data"]
        pipeline_customer_ids = [c["customer_id"] for c in pipeline_customers]
        
        print(f"✓ Step 3: Queried {len(pipeline_customers)} customers from database")
        
        # Verify at least some customers from mock are in pipeline
        common_ids = set(mock_customer_ids) & set(pipeline_customer_ids)
        assert len(common_ids) > 0, "No customers from mock server found in pipeline database"
        
        print(f"✓ Verified {len(common_ids)} customers present in both systems")
        
        # Step 4: Verify data integrity
        for customer_id in list(common_ids)[:3]:  # Check first 3 matching customers
            pipeline_cust = next(c for c in pipeline_customers if c["customer_id"] == customer_id)
            mock_cust = next(c for c in mock_customers if c["customer_id"] == customer_id)
            
            # Compare key fields (some may have formatting differences due to database storage)
            assert pipeline_cust["customer_id"] == mock_cust["customer_id"]
            assert pipeline_cust["first_name"] == mock_cust["first_name"]
            assert pipeline_cust["last_name"] == mock_cust["last_name"]
            assert pipeline_cust["email"] == mock_cust["email"]
        
        print(f"✓ Data integrity verified: Fields match between mock and pipeline")
