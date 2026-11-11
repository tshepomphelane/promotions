import os
import asyncio
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

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

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/__test/failure-mode")
def set_failure_mode(
    config: FailureConfig,
    x_test_control_token: str = Header(default="")
):
    global FAILURE_MODE, DELAY_SECONDS

    # do not allow failure simulation without a config token
    # Never allow failure simulation without a configured token.
    if not CONTROL_TOKEN:
        raise HTTPException(
            status_code=404,
            detail="Failure simulation is disabled"
        )

    if not secrets.compare_digest(
        x_test_control_token,
        CONTROL_TOKEN
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    FAILURE_MODE = config.mode
    DELAY_SECONDS = config.delay_seconds

    return {
        "failure_mode": FAILURE_MODE,
        "delay_seconds": DELAY_SECONDS
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