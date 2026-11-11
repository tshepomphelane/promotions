from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "http_server_requests_total",
    "HTTP requests handled by the fake profile API.",
    ("method", "route", "status_code"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration in seconds for the fake profile API.",
    ("method", "route"),
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5, 10, 30),
)


def record_request(method: str, route: str, status_code: int, elapsed: float) -> None:
    HTTP_REQUESTS.labels(method=method, route=route, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(elapsed)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)