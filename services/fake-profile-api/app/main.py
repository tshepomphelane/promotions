import os
import asyncio

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(title="Fake Customer Profile API")

FAILURE_MODE = os.getenv("FAILURE_MODE", "none")
DELAYS_SECONDS = float(os.getenv("DELAYS_SECONDS", "3"))
CONTROL_TOKEN = os.getenv("CONTROL_TOKEN", "")

CUSTOMERS = {
    "CUST-001": {"status": "ACTIVE"},
    "CUST-002": {"status": "INACTIVE"},
    "CUST-003": {"status": "ACTIVE"}
}

class FailureConfig(BaseModel):
    mode: str
    delay_seconds: float = 3

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/__test/failure-mode")
def set_failure_mode(
    config: FailureConfig,
    x_test_control_token: str = Header(default="")
):
    global FAILURE_MODE, DELAYS_SECONDS

    if not CONTROL_TOKEN or x_test_control_token != CONTROL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbiddn")

    if config.mode not in ["none", "slow", "error", "unauthorized"]:
        raise HTTPException(status_code=400, detail="Invalid failure mode")

    if config.delay_seconds < 0 or config.delay_seconds > 30:
        raise HTTPException(status_code=400, detail="Invalid delay")

    FAILURE_MODE = config.mode
    DELAYS_SECONDS = config.delay_seconds

    return {
        "failure_mode": FAILURE_MODE,
        "delay_seconds": DELAYS_SECONDS
    }

@app.get("/customers/{customer_id}/status")
async def get_customer_status(customer_id: str):

    if FAILURE_MODE == "slow":
        await asyncio.sleep(DELAYS_SECONDS)

    if FAILURE_MODE == "error":
        raise HTTPException(
            status_code=500,
            detail="Profile service failure"
        )

    if FAILURE_MODE == "unauthorized":
        raise HTTPException(
            status_code=401,
            detail="Authentication failure"
        )

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer