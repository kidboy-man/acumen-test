import os
import asyncio
import logging

import dlt
import httpx

logger = logging.getLogger(__name__)

MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://mock-server:5000")
PAGE_SIZE = 50


async def fetch_all_customers_from_flask():
    """Fetch all customers from Flask API with auto-pagination."""
    logger.info(f"Starting to fetch customers from {MOCK_SERVER_URL}")
    all_customers = []
    page = 1
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                logger.debug(f"Fetching page {page} with limit {PAGE_SIZE}")
                resp = await client.get(
                    f"{MOCK_SERVER_URL}/api/customers",
                    params={"page": page, "limit": PAGE_SIZE},
                )
                resp.raise_for_status()
                data = resp.json()
                records = data.get("data", [])
                
                if not records:
                    logger.debug(f"No more records on page {page}, stopping")
                    break
                    
                all_customers.extend(records)
                total = data.get("total", 0)
                
                logger.debug(f"Fetched {len(records)} records from page {page} (total so far: {len(all_customers)})")
                
                if page * PAGE_SIZE >= total:
                    logger.debug(f"Reached end of data (total: {total})")
                    break
                    
                page += 1
        
        logger.info(f"Successfully fetched {len(all_customers)} customers from Flask API")
        return all_customers
        
    except httpx.TimeoutException as e:
        logger.error(f"Timeout fetching from Flask API: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching from Flask API: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching from Flask API: {e}", exc_info=True)
        raise


def run_ingestion():
    """Fetch from Flask and load into Postgres using dlt. Returns number of records processed."""
    logger.info("Starting ingestion process")
    
    try:
        customers = asyncio.run(fetch_all_customers_from_flask())
        
        if not customers:
            logger.warning("No customers fetched from Flask API, skipping ingestion")
            return 0

        logger.info(f"Preparing to ingest {len(customers)} customers into database")

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable is required")
            raise ValueError("DATABASE_URL environment variable is required")

        @dlt.resource(
            primary_key="customer_id",
            write_disposition="merge",
            table_name="customers",
        )
        def customers_data():
            for c in customers:
                yield c

        logger.info(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
        
        pipeline = dlt.pipeline(
            pipeline_name="customer_ingest",
            destination=dlt.destinations.postgres(database_url),
            dataset_name="public",
        )
        
        logger.info("Starting dlt pipeline execution")
        pipeline.run(customers_data())
        
        logger.info(f"Successfully ingested {len(customers)} customers into database")
        return len(customers)
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise