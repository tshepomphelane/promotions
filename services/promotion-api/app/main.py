import os
import httpx

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Customer, CustomerActivity, Promotorion
from app.eligibility import evaluate_eligibility

app = FastAPI(
    title="Promotion Eligibility API",
    version="1.0.0"
)

PROFILE_SERVICE_URL = os.getenv(
    "PROFILE_SERVICE",
    "htpp://localhost:8001"
)

@app.on_event("startup")
def start():
    Base.metadata.create_all(bind=engine)

@app.get("health")
def health():
    return {"status": "healthy"}

@app.get("/customers/{customer_id}/promotions")
def get_promotions(
    customer_id: str,
    db: Session = Depends(get_db)
):
    # call external dependency before getting db session
    try:
        response = httpx.get(
            f"{PROFILE_SERVICE_URL}/customers/{customer_id}/status",
            timeout=1.0
        )
        response.raise_for_status()
        profile = response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Customer profile service unavailable"
        )

    if profile.get("status") != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Customer is not eligible"
        )

    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            details="Customer not found"
        )

    activity = db.query(CustomerActivity).filter(
        CustomerActivity.customer_id == customer_id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=404,
            detail="Customer activity not found"
        )

    promotions = db.query(Promotorion).filter(
        Promotorion.active.is_(True)
    ).all()

    eligible = evaluate_eligibility(activity, promotions)

    return {
        "customer_id": customer_id,
        "eligible_promotions": eligible
    }