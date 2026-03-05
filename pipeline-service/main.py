from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from database import get_db
from models.customer import Customer
from services.ingestion import run_ingestion

app = FastAPI(title="Customer Pipeline API")


@app.post("/api/ingest")
def ingest():
    """Fetch all data from Flask and upsert into PostgreSQL."""
    try:
        records_processed = run_ingestion()
        return {"status": "success", "records_processed": records_processed}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ingestion failed: {e!s}")


@app.get("/api/customers")
def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return paginated customers from the database."""
    try:
        total = db.query(Customer).count()
        offset = (page - 1) * limit
        rows = db.query(Customer).offset(offset).limit(limit).all()
    except ProgrammingError:
        return {"data": [], "total": 0, "page": page, "limit": limit}
    data = [_row_to_dict(r) for r in rows]
    return {"data": data, "total": total, "page": page, "limit": limit}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Return a single customer by id or 404."""
    try:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    except ProgrammingError:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _row_to_dict(customer)


def _row_to_dict(row: Customer) -> dict:
    return {
        "customer_id": row.customer_id,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "email": row.email,
        "phone": row.phone,
        "address": row.address,
        "date_of_birth": row.date_of_birth.isoformat() if row.date_of_birth else None,
        "account_balance": float(row.account_balance) if row.account_balance is not None else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
