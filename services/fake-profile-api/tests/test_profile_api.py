
import os
import time

from fastapi.testclient import TestClient

# test credentials before importing app
os.environ["CONTROL_TOKEN"] = "test-token"

from app.main import app

client = TestClient(app)
TOKEN = "test-token"
HEADERS = {
    "x-test-control-token": TOKEN
}

def set_mode(mode, delay_seconds=0):
    # configure fakeAPI failure mode helper
    return client.post(
        "/__test/failure-mode",
        headers=HEADERS,
        json={
            "mode": mode,
            "delay_seconds": delay_seconds
        }
    )

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_customer_status():
    set_mode("none")

    response = client.get("/customers/CUST-001/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

def test_slow_mode_delays_response():
    result = set_mode("slow", delay_seconds=0.2)

    assert result.status_code == 200

    start = time.perf_counter()

    response = client.get("/customers/CUST-001/status")

    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed >= 0.2

def test_error_mode():
    set_mode("error")

    response = client.get("/customers/CUST-001/status")

    assert response.status_code == 500

def test_unauthorized_mode():
    set_mode("unauthorized")

    response = client.get("/customers/CUST-001/status")

    assert response.status_code == 401

def test_negative_delay_is_rejected():
    response = set_mode("slow", delay_seconds=-1)

    assert response.status_code == 422

def test_excessive_delay_is_rejected():
    response = set_mode("slow", delay_seconds=60)

    assert response.status_code == 422

def test_invalid_failure_mode_is_rejected():
    response = set_mode("invalid")

    assert response.status_code == 422
