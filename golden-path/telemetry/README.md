# Telemetry standard

Use this when onboarding an HTTP service. It gives you metrics, traces and logs
that work with the SLO kit, with cost defaults that stop a service running up
the observability bill.

## 1. Add OpenTelemetry

Instrument inbound HTTP requests, outbound HTTP dependencies and the database
client. Set the resource `service.name` to the identifier used in deployment
and alerting.

```python
configure_telemetry(app, "my-service", engine)
```

Required environment variables (add them to your compose/deployment config):

```
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317
OTEL_TRACE_SAMPLE_RATIO=0.1
```

## 2. Metrics

Every HTTP service exposes `/metrics` with these RED metrics:

```
http_server_requests_total{method,route,status_code}
http_server_request_duration_seconds_bucket{method,route,status_code,le}
```

- Prometheus naming: durations in seconds, counters end in `_total`.
- Use route templates (`/customers/{customer_id}/promotions`), never raw paths.
- The SLO latency threshold must be one of the histogram buckets
  (`0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5`). The pipeline policy gate checks this.
- Allowed labels are small, bounded sets: `service`, `environment`, `method`,
  `route`, `status_code`, `dependency`, `outcome`, and a fixed `operation`
  name. Add a label only when it answers an operational question.
- Never use customer IDs, emails, request IDs or other unbounded values as
  labels. Use traces or logs to investigate a single request.

## 3. Traces

Add spans for inbound requests, outbound HTTP calls, database operations and
business rules that explain material latency. Propagate `traceparent` to
dependencies. Do not put secrets, tokens, raw SQL parameters or request and
response bodies in span attributes. Health checks and `/metrics` are excluded
from tracing.

## 4. Logs

Do not log credentials, tokens, payment data, customer profiles, raw SQL
parameters or complete request bodies. Per-request access logs are off:
metrics and traces already cover requests.

## 5. Cost controls (defaults)

| Control | Default | Where it is enforced | Override |
|---|---|---|---|
| Trace sampling | 10%, parent-based | `telemetry.py` | `OTEL_TRACE_SAMPLE_RATIO` (use 1.0 only locally) |
| Trace noise | health and metrics not traced | `telemetry.py` | none |
| Collector guardrails | memory limiter, batching | `otel-collector/config.yml` | platform team |
| Metric cardinality | per scrape: 2000 samples, 15 labels, 100-char values | `prometheus.yml` (scrape fails if exceeded) | ask the platform team |
| Scrape interval | 15s | `prometheus.yml` | platform team |
| Metric retention | 7 days / 2 GB (local) | Prometheus flags | platform team |
| Log level | WARNING, no access log | `UVICORN_LOG_LEVEL`, Dockerfile | raise to INFO temporarily during an incident, then revert |

Note: the SLO window is 28 days, but alert evaluation only needs hours of data.
28-day compliance reporting needs longer retention in the platform's
long-term store.

## 6. Run locally

```
docker compose up --build -d
curl http://localhost:8000/metrics
```

- Prometheus: http://localhost:19090
- Grafana: http://localhost:13000
- Jaeger: http://localhost:16686 (run with `OTEL_TRACE_SAMPLE_RATIO=1.0` to see every trace)