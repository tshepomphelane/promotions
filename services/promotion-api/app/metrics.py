from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "http_server_requests_total",
    "HTTP request handled by promotion-API",
    ("method", "route", "status_code"),
)

HTTP_REQUESTS_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "route"),
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5),
)

DB_POOL_SIZE = Gauge("db_pool_size", "Configured SQLAlchemy pool size.")
DB_POOL_CHECKED_IN = Gauge("db_pool_checked_in", "Connections currently idle in the pool.")
DB_POOL_CHECKED_OUT = Gauge("db_pool_checked_out", "Connections currently checked out.")
DB_POOL_OVERFLOW = Gauge("db_pool_overflow", "Current SQLAlchemy pool overflow connections.")
DB_POOL_TIMEOUTS = Counter("db_pool_checkout_timeouts_total", "Database pool checkout timeouts.")

def route_template(request: Request) -> str:
    # framework route template
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")

def record_request(method: str, route: str, status_code: int, elapsed: float) -> None:
    HTTP_REQUESTS.labels(method=method, route=route, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(elapsed)

def render_metrics(engine) -> Response:
    pool = engine.pool
    DB_POOL_SIZE.set(pool.size())
    DB_POOL_CHECKED_IN.set(pool.checkedin())
    DB_POOL_CHECKED_OUT.set(pool.checkedout())
    DB_POOL_OVERFLOW.set(pool.overflow())
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)