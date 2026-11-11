## End-to-end check against Docker compose
import os
import httpx
import pytest


"""
Run with:
  PROMOTION_API_URL=http://localhost:18000 \
  PROFILE_API_URL=http://localhost:18001 \
  PROFILE_CONTROL_TOKEN=local-assessment-token \
  pytest -q services/promotion-api/tests/test_api_integration.py
"""
PROMOTION_API_URL = os.getenv("PROMOTION_API_URL", "http://localhost:18000")
PROFILE_API_URL = os.getenv("PROFILE_API_URL", "http://localhost:18001")
PROFILE_CONTROL_TOKEN = os.getenv(
    "PROFILE_CONTROL_TOKEN",
    "local-assessment-token",
)

def set_profile_failure_mode(mode: str, delay_seconds: float = 0) -> None:
    response = httpx.post(
        f"{PROFILE_API_URL}/__test/failure-mode",
        headers={"x-test-control-token": PROFILE_CONTROL_TOKEN},
        json={"mode": mode, "delay_seconds": delay_seconds},
        timeout=5,
    )
    response.raise_for_status()

@pytest.fixture(autouse=True)
def reset_profile_failure_mode():
    set_profile_failure_mode("none")
    yield
    set_profile_failure_mode("none")

def get_promotions(customer_id: str) -> httpx.Response:
    return httpx.get(
        f"{PROMOTION_API_URL}/customers/{customer_id}/promotions",
        timeout=5,
    )

def test_active_customer_receives_matching_promotions():
    response = get_promotions("CUST-001")

    assert response.status_code == 200

    body = response.json()
    assert body["customer_id"] == "CUST-001"
    assert {
        promotion["promotion_id"]
        for promotion in body["eligible_promotions"]
    } == {
        "WELCOME001",
        "RSPENDER",
    }

def test_inactive_customer_is_not_eligible():
    response = get_promotions("CUST-002")

    assert response.status_code == 403
    assert response.json()["detail"] == "Customer is not eligible"

def test_unknown_customer_returns_not_found():
    response = get_promotions("CUST-404")

    assert response.status_code == 404

@pytest.mark.parametrize("mode", ["error", "unauthorized"])
def test_profile_dependency_failures_are_controlled(mode: str):
    set_profile_failure_mode(mode)

    response = get_promotions("CUST-001")

    assert response.status_code == 503
    assert response.json()["detail"] == "Customer profile service unavailable"

def test_slow_profile_dependency_times_out_quickly():
    set_profile_failure_mode("slow", delay_seconds=2)

    response = get_promotions("CUST-001")

    assert response.status_code == 503
    assert response.json()["detail"] == "Customer profile service unavailable"