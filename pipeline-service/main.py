from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
import logging
import os

from database import get_db
from models.customer import Customer
from services.ingestion import run_ingestion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Customer Pipeline API")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/ingest")
def ingest():
    """Fetch all data from Flask and upsert into PostgreSQL."""
    try:
        logger.info("Starting data ingestion from mock server")
        records_processed = run_ingestion()
        logger.info(f"Successfully ingested {records_processed} records")
        return {"status": "success", "records_processed": records_processed}
    except ValueError as e:
        logger.error(f"Validation error during ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Ingestion failed: {e!s}")


@app.get("/api/customers")
def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return paginated customers from the database."""
    try:
        logger.debug(f"Listing customers: page={page}, limit={limit}")
        total = db.query(Customer).count()
        offset = (page - 1) * limit
        rows = db.query(Customer).offset(offset).limit(limit).all()
        
        logger.info(f"Retrieved {len(rows)} customers from database (total: {total})")
        
        data = [_row_to_dict(r) for r in rows]
        return {"data": data, "total": total, "page": page, "limit": limit}
    except ProgrammingError as e:
        logger.warning(f"Database table not found, returning empty result: {e}")
        return {"data": [], "total": 0, "page": page, "limit": limit}
    except Exception as e:
        logger.error(f"Error in list_customers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Return a single customer by id or 404."""
    try:
        logger.debug(f"Looking up customer: {customer_id}")
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if customer is None:
            logger.warning(f"Customer not found: {customer_id}")
            raise HTTPException(status_code=404, detail="Customer not found")
        
        logger.info(f"Retrieved customer: {customer_id}")
        return _row_to_dict(customer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database query failed")


def _row_to_dict(row: Customer) -> dict:
    def format_date_or_datetime(value):
        """Convert date/datetime to ISO format string, handling string values from database."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)
    
    return {
        "customer_id": row.customer_id,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "email": row.email,
        "phone": row.phone,
        "address": row.address,
        "date_of_birth": format_date_or_datetime(row.date_of_birth),
        "account_balance": float(row.account_balance) if row.account_balance is not None else None,
        "created_at": format_date_or_datetime(row.created_at),
    }
