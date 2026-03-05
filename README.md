# Customer Data Pipeline

A data pipeline system with three microservices: a Flask mock API server, a FastAPI ingestion service, and PostgreSQL database.

## Services

### 1. Mock Server (Flask)
- **Port**: 5000
- **Purpose**: Provides mock customer data via REST API
- **Endpoints**:
  - `GET /api/health` - Health check
  - `GET /api/customers?page=1&limit=50` - Paginated customer data

### 2. Pipeline Service (FastAPI)
- **Port**: 8000
- **Purpose**: Ingests data from mock server into PostgreSQL
- **Endpoints**:
  - `POST /api/ingest` - Fetch all customers from mock server and ingest into database
  - `GET /api/customers?page=1&limit=10` - Retrieve customers from database
  - `GET /api/customers/{customer_id}` - Retrieve single customer

### 3. PostgreSQL Database
- **Port**: 5432
- **Purpose**: Stores customer data
- **Database**: `customer_db`

## Prerequisites

- Docker Desktop (running)
- Python 3.10+ (for local development)
- Make
- Git

Verify: `docker-compose --version` and `make --version`

## Environment Configuration

The `.env` file is **mandatory** for running services with Docker Compose. It contains database credentials and connection strings.

### Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `password` |
| `POSTGRES_DB` | PostgreSQL database name | `customer_db` |
| `DATABASE_URL` | PostgreSQL connection string for Pipeline Service | `postgresql://postgres:password@postgres:5432/customer_db` |

**Note**: For production, change `POSTGRES_PASSWORD` to a strong, unique password.

## Quick Start with Docker Compose

The easiest way to run all services together:

```bash
# 1. Set up environment file (required)
cp .env.example .env

# 2. Start all services
make compose-up
```

This starts all three services (PostgreSQL, Mock Server, and Pipeline Service) in Docker containers.

To stop:
```bash
make compose-down
```

View logs:
```bash
make compose-logs
```

## Running Services Locally (Development Mode)

To run services on your local machine with the database in Docker:

### 1. Set up environment and database

```bash
make db-up
```

This starts only PostgreSQL in Docker on `localhost:5432`.

### 2. In terminal 1, run the mock server

```bash
make run-native-mock
```

Flask runs on `http://localhost:5000`

### 3. In terminal 2, run the pipeline service

```bash
make run-native-pipeline
```

FastAPI runs on `http://localhost:8000`

### Setup shortcut

```bash
make run-native
```

This starts the database and prints instructions for running the other services.

## Available Make Commands

```bash
make help              # Show all available commands
make venv              # Create Python virtual environment
make install           # Install dependencies for both services
make install-test      # Install test dependencies
make db-up             # Start PostgreSQL container only
make db-down           # Stop all Docker services
make run-native-mock   # Run Flask server locally
make run-native-pipeline # Run FastAPI service locally
make run-native        # Start database + instructions for local services
make compose-up        # Start all services in Docker
make compose-down      # Stop all Docker services
make compose-build     # Build Docker images
make compose-logs      # View live logs from containers
make compose-test-up   # Start test services with isolated test database
make compose-test-down # Stop test services and clean up test database
make compose-test-logs # View live logs from test services
```

## Testing the Services

### Manual Testing with cURL

#### Test Flask Mock Server

```bash
curl http://localhost:5000/api/health
curl "http://localhost:5000/api/customers?page=1&limit=5"
```

#### Ingest Data into Pipeline

```bash
curl -X POST http://localhost:8000/api/ingest
```

#### Get Customers from Pipeline Database

```bash
curl "http://localhost:8000/api/customers?page=1&limit=5"
curl "http://localhost:8000/api/customers/cust_001"
```

## Integration Tests

Comprehensive pytest-based integration tests verify the complete data pipeline workflow.

### Test Database Isolation

Tests use a **separate test database** (`customer_db_test`) to:
- Keep production/development data clean
- Allow parallel and repeated test runs
- Prevent data pollution from failed tests
- Automatically clean up after test completion

The test database is configured via [docker-compose.test.yml](docker-compose.test.yml) (overlay configuration).

### Prerequisites for Testing

```bash
make install-test
```

This installs pytest and httpx dependencies into your virtual environment.

### Running Tests - Automatic Setup & Cleanup (Recommended)

The simplest way to run tests - services start, tests execute, and everything cleans up automatically:

```bash
make test
```

Or with verbose output:
```bash
make test-verbose
```

**What happens:**
1. Test services start (mock server, pipeline service, test database)
2. Integration tests run
3. Test services and test database are automatically cleaned up

### Running Tests - Manual Service Management

If you prefer to manage services manually:

**Terminal 1 - Start test services:**
```bash
make compose-test-up
```

**Terminal 2 - Run the tests:**
```bash
.venv/bin/pytest tests/ -v
```

**Terminal 3 (optional) - View test service logs:**
```bash
make compose-test-logs
```

When done, clean up:
```bash
make compose-test-down
```

### Test Coverage

**Mock Server Tests (4 tests)**
- Health check endpoint validation
- Customer list with default pagination
- Custom pagination parameters
- Customer data structure and required fields

**Pipeline Ingestion Tests (1 test)**
- Data ingestion from mock server into test database
- Record count verification (22 customers)

**Pipeline Query Tests (5 tests)**
- Paginated customer retrieval from database
- Single customer lookup by ID
- 404 error handling for non-existent customers
- Data type validation for all fields
- Pagination parameter handling

**End-to-End Tests (1 test)**
- Complete workflow: Mock Server → Ingestion → Database Queries
- Data integrity verification between systems
- Field consistency checks

### Test Output Example

```
tests/test_integration.py::TestMockServer::test_health_check PASSED                    [  9%]
tests/test_integration.py::TestMockServer::test_list_customers_default_pagination PASSED [ 18%]
tests/test_integration.py::TestMockServer::test_customer_data_structure PASSED           [ 36%]
tests/test_integration.py::TestPipelineIngestion::test_ingest_data PASSED                [ 45%]
tests/test_integration.py::TestPipelineQueries::test_list_customers_from_database PASSED [ 54%]
tests/test_integration.py::TestPipelineQueries::test_customer_by_id PASSED               [ 72%]
tests/test_integration.py::TestEndToEnd::test_complete_workflow PASSED                   [100%]

============================== 11 passed in 1.43s ==============================
```

## Project Structure

```
.
├── mock-server/              # Flask API serving customer data
│   ├── app.py               # Flask application
│   ├── Dockerfile           # Docker configuration for mock server
│   ├── requirements.txt      # Python dependencies
│   └── data/
│       └── customers.json    # Mock customer data
│
├── pipeline-service/         # FastAPI service for data ingestion
│   ├── main.py              # FastAPI application with endpoints
│   ├── database.py          # SQLAlchemy database configuration
│   ├── Dockerfile           # Docker configuration for pipeline service
│   ├── requirements.txt      # Python dependencies
│   └── models/
│       └── customer.py       # SQLAlchemy Customer model
│   └── services/
│       └── ingestion.py      # Data ingestion logic using dlt
│
├── tests/                       # Integration tests
│   ├── test_integration.py       # Pytest integration tests (11 test cases)
│   └── conftest.py               # Pytest configuration and fixtures
│
├── docker-compose.yml            # Docker Compose configuration for development/production
├── docker-compose.test.yml       # Overlay config for test environment (isolated test DB)
├── Makefile                      # Build automation and service management
├── requirements.txt              # Test dependencies (pytest, httpx)
├── .env.example                  # Environment variables template
└── README.md                     # This file
```

## How It Works

1. **Mock Server** (Flask) reads `customers.json` and exposes it via REST API with pagination
2. **Pipeline Service** (FastAPI) fetches data from Mock Server via `/api/ingest` endpoint
3. **dlt Library** handles data transformation and loading into PostgreSQL using merge disposition
4. **Integration Tests** verify the complete workflow using an isolated test database (`customer_db_test`)
4. **FastAPI** provides endpoints to query ingested customers from the database

## Database Schema

The `customers` table is created automatically with these fields:
- `customer_id` (String, Primary Key)
- `first_name`, `last_name` (String)
- `email` (String)
- `phone` (String, optional)
- `address` (Text, optional)
- `date_of_birth` (Date, optional)
- `account_balance` (Decimal, optional)
- `created_at` (DateTime, optional)
