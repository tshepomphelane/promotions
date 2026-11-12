# Telemetry standard

Use this when onboarding an HTTP service. It provides guidelines to operate a service without identifiers into observability costs.

## 1. ADD OpenTelemetry

Instrument inboud HTTP requests, outbound HTTP dependencies, and database client. Set OpenTelemetry resource `service.name` to the service identifier used in deployment and alerting.

```
configure_telemetry(app, "my-service", engine)
```
Required environment variables:
```
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317
OTEL_TRACE_SAMPLE_RATIO=0.1
```
These must be added to docker-compose file

## 2. Metrics

Every HTTP ervice must expose `/metrics` with the following RED metrics:

```
http_server_requests_total{method,route,status_code}
http_server_request_duration_seconds_bucket{method,route,status_code,le}
```

Metrics use Prometheus naming convention: duration are in seconds. Use route templates such as `/customers/{customer_id}/promotions`

Allowed metric labels are small, bounded sets: `service`, `environment`,
`method`, `route`, `status_code`, `dependency`, `outcome`, and a fixed
`operation` name. Add a label only when it answers an operational question.

Use traces or logs to investigate a single customer or request instead.

## 3. Traces

Add spans for inbound requests, outbound HTTP calls, database operations,
and business rules that explain material latency. Propagate the traceparent header to dependencies. Do not put secrets, access tokens, raw SQL parameters, or full request/response bodies in span
attributes.

## 4. Logs

Do not log credentials, tokens, payment data, customer profiles, raw SQL parameters, or complete request bodies.

## Build and run the app

```
docker compose up --build -d
curl http://localhost:8000/metrics
```

#### View metrics:
- Prometheus: http://localhost:19090
#### dashboards: 
- Grafana: http://localhost:13000 
#### Traces: 
- Jaeger: http://localhost:16686.