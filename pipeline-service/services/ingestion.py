import os
import logging

import dlt
import httpx

logger = logging.getLogger(__name__)

MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://mock-server:5000")
PAGE_SIZE = 50


async def fetch_all_customers_from_flask():
    """Fetch all customers from Flask API with auto-pagination."""
    all_customers = []
    page = 1
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            resp = await client.get(
                f"{MOCK_SERVER_URL}/api/customers",
                params={"page": page, "limit": PAGE_SIZE},
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("data", [])
            if not records:
                break
            all_customers.extend(records)
            total = data.get("total", 0)
            if page * PAGE_SIZE >= total:
                break
            page += 1
    return all_customers


def run_ingestion():
    """Fetch from Flask and load into Postgres using dlt. Returns number of records processed."""
    import asyncio
    customers = asyncio.run(fetch_all_customers_from_flask())

    if not customers:
        return 0

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    @dlt.resource(
        primary_key="customer_id",
        write_disposition="merge",
        table_name="customers",
    )
    def customers_data():
        for c in customers:
            yield c

    pipeline = dlt.pipeline(
        pipeline_name="customer_ingest",
        destination=dlt.destinations.postgres(database_url),
        dataset_name="public",
    )
    pipeline.run(customers_data())
    return len(customers)