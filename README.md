# Promotion eligibility service and the SRE golden path

This repo has two things:

1. **A real service**: the promotion eligibility API (`GET /customers/{id}/promotions`),
   used here as the worked example.
2. **The golden path**: a kit that gives any team SLOs, alerts, telemetry, a runbook
   and a safe pipeline by writing one spec file and following the steps below.
   You build and run your service; the platform team keeps the kit working.

## What you get

| You do | You get |
|---|---|
| Write one SLO spec (10 lines) | Recording rules, fast-burn (page) and slow-burn (ticket) alerts, a "service down" alert, and optionally a DB pool alert |
| Copy the telemetry setup (about 30 lines) | RED metrics, traces in Jaeger, safe cost defaults |
| Fill in the runbook template | A one-page runbook linked from every alert |
| Call one reusable workflow | Tests, SLO and runbook checks, image scan, deploy smoke test |

Expect roughly half a day for a service that already has an HTTP API.

## Try it in 5 minutes

Needs Docker with Compose. Run from the repo root:

```bash
docker compose up -d --build --wait
curl localhost:8000/customers/CUST-001/promotions
```

| What | Where |
|---|---|
| Promotion API / fake profile API | http://localhost:8000 / http://localhost:8001 |
| Prometheus (alerts, rules) | http://localhost:19090 |
| Grafana (login admin / admin) | http://localhost:13000 |
| Jaeger (traces) | http://localhost:16686 (run with `OTEL_TRACE_SAMPLE_RATIO=1.0` to see every trace) |

Test customers: `CUST-001` and `CUST-003` (active), `CUST-002` (inactive, returns 403),
anything else returns 404.

## Onboard your service

### 1. Expose metrics and traces
Copy `services/promotion-api/app/metrics.py` and `telemetry.py` into your service and follow
[`golden-path/telemetry/README.md`](golden-path/telemetry/README.md). Your service must
expose `/metrics` with `http_server_requests_total` and
`http_server_request_duration_seconds_bucket`, labelled `method`, `route`, `status_code`
(route templates, never raw paths).

### 2. Write your SLO spec
Copy `golden-path/slo/service.toml` and edit it:

```toml
service = "my-service"
job = "my-service"                        # Prometheus job name
route = "/things/{id}"                    # route template you measure
target = 0.999                            # 99.9% of requests good
window = "28d"
latency_threshold_seconds = 0.3           # must be a histogram bucket
owner = "my-team"
runbook = "docs/runbooks/my-service.md"
db_pool = false                           # true if you export db_pool_* metrics
```

A request is **good** if it returns anything except a 5xx *and* finishes within the latency
threshold. 4xx responses (for example "customer not found") are not counted against you.

### 3. Generate the rules and register your service

```bash
python3 golden-path/slo/generate_rules.py my-service.toml \
  --output observability/prometheus/generated/my-service-slo-rules.yml
```

Add a scrape job for your service to `observability/prometheus/prometheus.yml` (copy the
`promotion-api` block), then `docker compose up -d --build prometheus`. Rules appear at
`/rules` and alerts at `/alerts`.

### 4. Write your runbook
Copy `golden-path/runbooks/TEMPLATE.md` to the path in your spec and fill it in. A finished
example is [`golden-path/runbooks/promotion-api.md`](golden-path/runbooks/promotion-api.md).
Alerts link to it, so it is the first page whoever is on call will read.

### 5. Use the pipeline
Add a small workflow that calls the shared one:

```yaml
jobs:
  ci:
    uses: ./.github/workflows/golden-path-ci.yml
    with:
      service_name: my-service
      service_path: services/my-service
      slo_spec: my-service.toml
      rules_output: observability/prometheus/generated/my-service-slo-rules.yml
      test_args: "-q --ignore=tests/test_api_integration.py"
```

The pipeline runs your unit tests, then a **policy gate** that fails if your SLO spec is
invalid, the committed rules are out of date, the latency threshold is not a real histogram
bucket, or the runbook is missing or still has `FILL IN` placeholders. It then builds and
scans the image (fails on HIGH or CRITICAL findings) and, on `main`, deploys to a test
environment and smoke-tests it. Run the gate yourself any time:

```bash
python3 golden-path/pipeline/policy_gate.py --spec my-service.toml \
  --rules observability/prometheus/generated/my-service-slo-rules.yml
```

## Alerts and their meaning

| Alert | Means | Severity |
|---|---|---|
| `...ErrorBudgetFastBurn` | Budget burning 14.4x too fast (2% of 28 days' budget per hour) | page |
| `...ErrorBudgetSlowBurn` | Budget burning 6x too fast (5% every 6 hours) | ticket |
| `...Down` | Prometheus cannot scrape the service (or its data is gone) | page |
| `...DbPoolExhausted` | Requests are failing because no DB connection is free | page |

A 99.9% target leaves an error budget of 0.1% of requests over 28 days, about 40 minutes
of full outage.

## Error budget policy (proposed)

The ticket does not say what happens when the budget runs out, so this is a proposal.

| Budget remaining (28 days) | What the team does |
|---|---|
| Above 50% | Normal work. Ship as usual. |
| 25% to 50%, or the slow-burn ticket is open | Reliability work goes to the top of the next sprint. |
| Below 25% | Only reliability and security changes ship. New features wait. |
| Exhausted (0%) | Feature freeze for this service. Releases need product owner and SRE sign-off. The freeze lifts when the budget is back above 25%. |

A fast-burn page means stop and fix, whatever the budget level. After any incident, check
the remaining budget and apply the table.

**Assumptions to confirm with the product team:**
- 503s caused by our dependencies (customer-profile service, database) count against *our*
  SLO, because customers see the failure either way. If the profile service has its own SLO,
  we could exclude its failures.
- A promotional campaign is a business-critical release: it may go ahead during a freeze if
  the product owner and SRE agree and a rollback plan exists.
- Stale promotion rules (up to 30 seconds old, longer during a database problem) are
  acceptable for eligibility decisions.
- Peak traffic is about 800 req/s for 30 minutes after the Friday 18:00 email; steady state
  is about 60 req/s.

## Practise failure

```bash
# Steady load (60 req/s). Use -e SCENARIO=peak for the campaign ramp (see note below)
docker compose --profile load run --rm k6 run /scripts/promotion.js -e DURATION=3m

# Make the customer-profile dependency misbehave: slow, error or unauthorized (none resets)
curl -X POST localhost:8001/__test/failure-mode \
  -H "X-Test-Control-Token: local-assessment-token" \
  -H "Content-Type: application/json" \
  -d '{"mode":"slow","delay_seconds":1}'
```

The database pool exhaustion drill is described in
[`golden-path/runbooks/promotion-api.md`](golden-path/runbooks/promotion-api.md).
The `peak` scenario asks one local container for 800 req/s; expect it to saturate. Measure
where it breaks and size replicas from that (replicas x pool size must stay below Postgres
`max_connections`).

## Cost defaults

Observability is billed by usage, so the kit sets safe defaults: 10% trace sampling,
health and metrics endpoints not traced, per-scrape series and label limits, 7-day local
retention, warning-level logs with no per-request access log. Details and how to ask for an
exception are in the telemetry standard. Never use customer IDs or other unbounded values as
metric labels.

## Repo map

| Path | What it is |
|---|---|
| `services/promotion-api` | The example service, with tests |
| `services/fake-profile-api` | Fake dependency with a switch to make it fail |
| `golden-path/slo` | SLO spec and rule generator |
| `golden-path/telemetry` | Telemetry standard and cost controls |
| `golden-path/runbooks` | Runbook template and the filled-in example |
| `golden-path/pipeline` | Pipeline policy gate (workflow in `.github/workflows`) |
| `observability` | Prometheus, Grafana and OpenTelemetry Collector config |
| `load-tests` | k6 load script |
| `DECISIONS.md` | Decisions, assumptions, trade-offs, gaps |

## Known gaps

No Alertmanager (alerts are visible in Prometheus only), telemetry code is copied rather
than packaged as a library, and there is no cloud deployment. See `DECISIONS.md`.