import os
import asyncio
import secrets
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, Field

from app.metrics import metrics_response, record_request

app = FastAPI(title="Fake Customer Profile API")

# failure simulation config
FAILURE_MODE = os.getenv("FAILURE_MODE", "none")
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "3"))
CONTROL_TOKEN = os.getenv("CONTROL_TOKEN", "")

# test users
CUSTOMERS = {
    "CUST-001": {"status": "ACTIVE"},
    "CUST-002": {"status": "INACTIVE"},
    "CUST-003": {"status": "ACTIVE"}
}

class FailureConfig(BaseModel):
    mode: Literal["none", "slow", "error", "unauthorized"]
    delay_seconds: float = Field(default=3, ge=0, le=30)

def require_control_token(x_test_control_token: str) -> None:
    # Keep fault injection unavailable unless enabled and authorised
    if not CONTROL_TOKEN:
        raise HTTPException(status_code=404, detail="Failure simulation is disabled")

    if not secrets.compare_digest(x_test_control_token, CONTROL_TOKEN):
        raise HTTPException(status_code=403, detail="Forbidden")

@app.middleware("http")
async def request_metrics(request: Request, call_next):
    started = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        record_request(
            method=request.method,
            route=route,
            status_code=status_code,
            elapsed=time.perf_counter() - started,
        )

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()

@app.post("/__test/failure-mode")
def set_failure_mode(
    config: FailureConfig,
    x_test_control_token: str = Header(default="")
):
    global FAILURE_MODE, DELAY_SECONDS

    require_control_token(x_test_control_token)

    FAILURE_MODE = config.mode
    DELAY_SECONDS = config.delay_seconds

    return {
        "failure_mode": FAILURE_MODE,
        "delay_seconds": DELAY_SECONDS,
    }

@app.get("/__test/failure-mode")
def get_failure_mode(x_test_control_token: str = Header(default="")):
    # verify injected failure state via a load test
    require_control_token(x_test_control_token)

    return {
        "failure_mode": FAILURE_MODE,
        "delay_seconds": DELAY_SECONDS,
    }

@app.get("/customers/{customer_id}/status")
async def get_customer_status(customer_id: str):

    # slow external depency simulation
    if FAILURE_MODE == "slow":
        await asyncio.sleep(DELAY_SECONDS)

    # dependency server failure simulation
    if FAILURE_MODE == "error":
        raise HTTPException(status_code=500, detail="Profile failure")

    # rejected credentials simulation    
    if FAILURE_MODE == "unauthorized":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer