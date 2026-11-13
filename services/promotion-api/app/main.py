import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.database import Base, SessionLocal, engine
from app.eligibility import evaluate_eligibility
from app.metrics import (
    DB_POOL_TIMEOUTS,
    record_request,
    render_metrics,
    route_template,
)
from app.models import CustomerActivity
from app.telemetry import configure_telemetry
from app.rules_cache import load_promotions

app = FastAPI(title="Promotion Eligibility API", version="1.0.0")

configure_telemetry(app, "promotion-api", engine)

PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL", "http://localhost:8001")
# Must stay under the 300ms SLO latency threshold
PROFILE_TIMEOUT_SECONDS = float(os.getenv("PROFILE_TIMEOUT_SECONDS", "0.25"))

profile_client = httpx.Client(
    timeout=httpx.Timeout(PROFILE_TIMEOUT_SECONDS),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
def shutdown():
    profile_client.close()

@app.middleware("http")
async def request_metrics(request: Request, call_next):
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

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return render_metrics(engine)

@app.get("/customers/{customer_id}/promotions")
def get_promotions(customer_id: str):
    # Dependency call first, so a slow profile service never holds DB connection.
    try:
        response = profile_client.get(
            f"{PROFILE_SERVICE_URL}/customers/{customer_id}/status"
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Customer not found")
        response.raise_for_status()
        profile = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503, detail="Customer profile service unavailable"
        )

    if profile.get("status") != "ACTIVE":
        raise HTTPException(status_code=403, detail="Customer is not eligible")

    try:
        with SessionLocal() as db:
            activity = (
                db.query(CustomerActivity)
                .filter(CustomerActivity.customer_id == customer_id)
                .first()
            )
            if not activity:
                raise HTTPException(status_code=404, detail="Customer not found")

            promotions = load_promotions(db)
            eligible = evaluate_eligibility(activity, promotions)
    except PoolTimeoutError:
        # Pool exhausted: fail fast and tell clients to back off.
        DB_POOL_TIMEOUTS.inc()
        raise HTTPException(
            status_code=503,
            detail="Database busy",
            headers={"Retry-After": "1"},
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )

    return {"customer_id": customer_id, "eligible_promotions": eligible}