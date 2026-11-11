import os
import httpx
import time

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine, SessionLocal
from app.models import Customer, CustomerActivity, Promotion
from app.eligibility import evaluate_eligibility

app = FastAPI(
    title="Promotion Eligibility API",
    version="1.0.0"
)

PROFILE_SERVICE_URL = os.getenv(
    "PROFILE_SERVICE_URL",
    "http://localhost:8001"
)

profile_client = httpx.Client(
    timeout=httpx.Timeout(1.0),
    limits=httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20
    )
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
def shutdown():
    profile_client.close()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/customers/{customer_id}/promotions")
def get_promotions(customer_id: str):

    # Call external dependency
    try:
        response = profile_client.get(
            f"{PROFILE_SERVICE_URL}/customers/{customer_id}/status"
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Customer not found"
            )

        response.raise_for_status()
        profile = response.json()

    except HTTPException:
        raise

    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Customer profile service unavailable"
        )

    if profile.get("status") != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Customer is not eligible"
        )

    # then get db database session
    try:
        with SessionLocal() as db:

            customer = db.query(Customer).filter(
                Customer.id == customer_id
            ).first()

            if not customer:
                raise HTTPException(
                    status_code=404,
                    detail="Customer not found"
                )

            activity = db.query(CustomerActivity).filter(
                CustomerActivity.customer_id == customer_id
            ).first()

            if not activity:
                raise HTTPException(
                    status_code=404,
                    detail="Customer activity not found"
                )

            promotions = db.query(Promotion).filter(
                Promotion.active.is_(True)
            ).all()

            eligible = evaluate_eligibility(activity,promotions)

            return {
                "customer_id": customer_id,
                "eligible_promotions": eligible
            }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable"
        )
    
@app.middleware("http")
async def request_metrics(request, call_next):
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        record_request(
            method=request.method,
            route=route_template(request),
            status_code=status_code,
            elapsed=time.perf_counter() - started,
        )