# Decisions

Everything runs locally with `docker compose up -d --build --wait`. <br>
Terms: SLI/SLO = service level indicator/objective.

**Prequisites**
- Docker engine running locally
- Python v3+ installed locally
- pytest installed locally (optional)

## 1. Key decisions and what I rejected

**SLI: what counts as a good request.** A request is good if it is not a 5xx and finishes
within 300 ms, measured at the service from the request histogram (`le="0.3"`).
4xx (inactive or unknown customer) are good: the service responded correctly.
Rejected: measuring only availability, because a slow response during a promotion is a
failure for the customer; synthetic probing, because there is no real edge locally
(*listed under one more sprint*).

**SLO and alerts.** 99.9% over 28 days (about 40 minutes of full outage). Multi-window
burn-rate alerts: page at 14.4x burn when both 5m and 1h window exceeds it (2% of budget
per hour), ticket at 6x over 30m and 6h. Rejected: a single threshold on error rate
(pages on short blips, misses slow burns).

**SLO as code.** One TOML spec per service, a small stdlib-only Python generator produces
the recording rules and alerts. Rejected: Sloth/Pyrra (another tool to run and explain
for a three-day task; a platform team could adopt one later). Gap: `window` is validated
as present but the 28-day wording and rule windows are fixed in the generator.

**Alerts on the scrape, not just the ratio.** `...Down` fires on `up == 0` or a missing
target. With no traffic the request ratios return no data, a full outage would be silent. This also catches a scrape rejected for exceeding `sample_limit`.

**Pool exhaustion alert signal.** `rate(db_pool_checkout_timeouts_total[2m]) > 0`.
It counts requests turned away because of the pool, its normal value is `0`
and it names the cause within a minute. Rejected: alerting on the pool gauge
(can sit at 100%, sampled every 15s) and relying on the burn-rate alert
alone does not tell us why the budget is burning.

**Timeouts and pool.** Pool size 5, no overflow, pool timeout 200ms, profile timeout
250ms, Postgres statement timeout 500ms. Anything slower than the 300ms threshold has
already burned budget, the service fails fast with 503 and `Retry-After`.
Sizing rule for the kit: replicas x pool size must stay under Postgres `max_connections`.

**No retries to the profile service.** At the 800 req/s peak, retries multiply load on a
struggling dependency. Failures return 503 quickly. Rejected: retries, circuit breaker
(*listed under one more sprint*).

**The mitigation built into the service.** Promotion rules are cached for 30s, when a
refresh fails, one request retries while the rest keep serving the last good rules
(`rules_cache_stale_served_total` shows it is active); statement timeout bounds how long
a stuck query holds a connection. Rejected as first moves: raising the pool size (more
connections into a blocked database), restarting the service (empties the cache),
a circuit breaker. Trade-offs: rule changes take up to 30s to show, stale rules are served
during an outage on purpose, and a restart during a lock has no stale rules to serve.

**Dependency failures count against our SLO.** Customers see the failure either way.

**Telemetry.** Metrics via `prometheus_client` (naming and label rules in the telemetry
standard), traces via OpenTelemetry to a collector and Jaeger. Cost defaults: 10%
parent-based sampling, health and metrics not traced, per-scrape limits (2000 samples,
15 labels), 15s scrape interval, 7d / 2GB retention, warning-level logs, no access log.
Known trade-off: exceeding `sample_limit` drops the whole scrape, which caps the bill but
**shows up as a gap in the SLI**.

**Pipeline.** GitHub Actions reusable workflow (`workflow_call`): unit tests, policy gate,
image build, Trivy scan (HIGH/CRITICAL fail), then a deploy job that brings the stack up
with compose, smoke-tests it and runs the integration tests. The policy gate fails when the
SLO spec is invalid, the committed rules are stale, the latency threshold is not a histogram
bucket, or the runbook is missing or has `FILL IN` placeholders. I chose GitHub Actions
because my repo is hosted on GitHub.
Rejected for now: Dockerfile hardening checks and SBOM in the gate.

## 2. How I approached the service build

Kept small on purpose: one real endpoint (`GET /customers/{id}/promotions`) including health and
metrics, three tables, plain SQLAlchemy, synchronous handlers, schema in `init.sql`.
The fake profile service has one fault switch (slow, error, unauthorized) behind a token.

I chose not to build: authentication, write APIs, pagination, a migration tool, async,
in-app rate limiting, multiple workers or replicas, a shared telemetry library.
I have spent a lot of effort on the failure behaviour (timeouts, pool, cache) and what an SRE or Platform Engineer would 
need to operate it, because that is what the kit has to carry.

## 3. Where I used AI

I used AI (ChatGPT and Claude) in three places. 

| Area | What I asked | What AI produced | What I changed or rejected |
|---|---|---|---|
| Mitigation ON/OFF comparative strategy | Design a comparative mitigation testing strategy, compare application reliability and performance with selected mitigation mechanisms disabled and enabled. Define the baseline configuration (Mitigation OFF), Define the protected configuration (Mitigation ON), Configure k6 workloads, Collect application, compare SLI/SLO performance | k6 scripts, Test configuration, PromQL queries | Rejected PromQL queries |
| SLO Dashboard design | review my code and generate loadtest test data | docker compose with test queries | Teste and accepted the results |
| SLO kit (generator fix) | I want to establish an SLO (and alerts) framework for fake-pofile-api and promotion-api. Design SLO targets and promotion rules | golden path/SLO, pool alerts, and fixed YAML output | promotion rules |
| Error budgeting and burt-rate alerting | Design an error-budget management and alerting framework that uses Prometheus, Grafana, and OpenTelemetry. Provide: Error-budget calculation examples, PromQL recording rules, Prometheus alerting rules, Grafana dashboard panels, Alert severity recommendations, Incident response actions, Deployment freeze and release-management policies. Explain how to avoid alert fatigue and why static error-rate thresholds alone are insufficient. |     30-day rolling error budgets, Error-budget consumption, Fast-burn and slow-burn detection, Multi-window, multi-burn-rate alerting, Critical incident escalation. | Accepted the results
| OpenTelemetry Collector configuration | Help me design a production-ready OpenTelemetry Collector configuration for AKS or Docker environment. Requirements:     Collect application metrics, logs and traces. Receive OTLP over gRPC and HTTP, Collect fake-profile-api and promotion-api metrics. |     Apply batching and memory limiting, Configure filtering and attribute processing, Export metrics to Prometheus-compatible infrastructure, Export traces to our selected tracing backend, Export logs to our centralised logging platform. | Complete Collector configuration in YAML, Explanation of receivers, processors, exporters and extensions. |
| k6 Load testing strategy & k6 scripts| Act as a performance test engineer and create productio ready k6 test scripts | Implementation roadmap using Grafan k6 and integration with OpenTelemetry. Complete JS test script| Test script |
| SLO Driven performance Testing | Implement SLO driven perf testing, reliability targets - Availability SLO: 99%, Latency SLO: 95% of request below 300ms, Error-rate SLO: below 0.1% | SLO validation report template, CI approach | modified the CI and tailord it to the promotion APIs |
| Runbook, README, this document, cost estimate | Update README.md for the promotions repo and add required step to run the service(s) using docker compose. Using the Azure Cost Calculater, add estimates for hosting this solution in Azure Kubernetes Service | Drafts files | Updated the drafts and added links to accessing and `curl` executable commands to browse the services |

I have also had a lot of spelling errors and not matching ports numbers in the services and docker compose which resulted in image build failures and services not running.

Things I verified myself rather than trusting the output: I ran the
pool drill twice, ran `promtool check rules`, ran the policy gat and followed the README instructions.

## 4. Questions and assumptions

Questions for the product team (NOT SENT):
1.	What are the exact promotion eligibility rules, and who owns changes to them?
2.	What should happen if the customer-profile service is unavailable? Should we fail closed, return a temporary error, or use cached customer status?
3. Should failures caused by the customer-profile service count against our SLO?
4. Is a 28-day 99.9% objective with a 300 ms threshold what the campaign needs?
5. How stale may promotion rules be?
6. What does eligibility need in the way of authentication and audit logging?
7.	Are there specific campaign periods or promotions when the service must be available, and are deployments prohibited during those periods?
8.	When the error budget is exhausted, should releases be frozen automatically or should the product team decide based on incident severity?
9.	Who owns the service and receives production alerts?
10.	Is the 300ms latency requirement measured at the API boundary, including the profile dependency?

Assumptions I made:
- Dependency 503s count against our SLO.
- Steady state is 60 req/s, peak 800 req/s for 30 minutes after the Friday 18:00 email.
- Rules up to 30s old (longer during a database problem) are acceptable.
- A campaign may be released during a freeze with product owner and SRE sign-off.
- Error budget policy: details in the README (50% / 25% / 0% levels), proposed, not agreed.
- Single region, single database, no authentication in scope.

## 5. Rough monthly cost (production, Azure) - AI response

Assumptions: Azure Container Apps (consumption), 2 replicas always on at 0.5 vCPU and 1 GiB,
extra replicas for the 30-minute Friday peak; PostgreSQL Flexible Server B2s with 32 GiB
(no high availability); about 161M requests per month (60 req/s all month plus about
6M extra for four to five peaks); managed Prometheus-style metrics and Application Insights
for traces; 10% trace sampling at about 5 spans per trace and about 1 KB per span.

| Item | Calculation | Monthly |
|---|---|---|
| Container Apps compute | 2 x (0.5 vCPU, 1 GiB) always active, minus free grant | ~$72 |
| Container Apps peak replicas | 4 extra x 30 min x 4.3 Fridays | ~$1 |
| Container Apps requests | (161M - 2M free) x $0.40 per million | ~$64 |
| PostgreSQL B2s + storage | $30 to $85 compute depending on region, plus storage | ~$55 |
| Traces | 16M traces x 5 spans = 81M spans = about 81 GB x $2.30 (5 GB free) | ~$175 |
| Metrics | about 300 series x 2 replicas x 15 s scrapes = about 104M samples | ~$2 |
| Logs | warning level only, inside the free 5 GB | $0 |
| **Total** | | **~$370 ($330 - $450)** |

What drives it:
- Traces are almost half the bill. At 100% sampling they would cost about $1,800 a month;
  at 1% about $10. The 10% default and not tracing health checks matter.
- The `sample_limit` of 2000 caps metrics at about $11 a month for two replicas even if a
  cardinality bug appears.
- Container Apps charges per request, which is about 40% of compute here; at this volume
  AKS or a dedicated plan may be cheaper (to evaluate).
- Not included: edge (Front Door has a base fee plus request and egress charges),
  high availability for the database, egress, DNS, the CI runner.
- Numbers to measure instead of assume: series count (`count({job="promotion-api"})`) and
  spans per trace (in Jaeger).

## 6. Golden-path parts I did not build (half a page each)

### Azure IaC module (Terraform)
One reusable module `modules/service` that a team calls with a handful of inputs: service
name, owner, environment, cost centre, image, CPU and memory, min and max replicas,
database SKU. It creates the resource group, Log Analytics workspace, Container Apps
environment and app, a user-assigned managed identity, the PostgreSQL Flexible Server and
database, and Key Vault references for secrets (no secrets in state or variables).

Tags are enforced in two layers. In the module, a `tags` object variable has a validation
block requiring `owner`, `service`, `environment` and `cost_centre` to be present and
non-empty; every resource takes the same map. Because module validation only protects
people who use the module, Azure Policy (deny or append on missing tags) is the backstop
at subscription level. Cost guardrails: a `max_replicas` cap bounds spend, a budget alert
per cost centre, and  database SKU defaults. CI runs `terraform fmt -check` and
`terraform validate` (no cloud account required) in the existing pipeline template.
Why I did not build it: it is the part that is least relevant to SLO and telemetry, and
the three-day limit meant choosing the pipeline.

### Edge and security
Azure Front Door in front of the Container App, defined in Terraform. TLS terminates at
the edge with a managed certificate (issued and renewed automatically, custom domain
validated by DNS). A WAF policy adds rate limiting per client IP (*start in log-only mode,
tune from real traffic, remembering the Friday email creates a legitimate spike*) and
managed rule sets where the SKU allows them. 

The origin is reachable only through the
edge: Container Apps ingress restricted to the Front Door service tag, and the app or
ingress checks the `X-Azure-FDID` header against our profile so another Front Door
cannot reach us. Certificate expiry alert: a blackbox probe exporting
`probe_ssl_earliest_cert_expiry` with an alert under 14 days, which works whatever issues
the certificate. Locally, I would implement this using Caddy with TLS and rate limiting.

## 7. Known gaps and shortcuts, and what I cut for three days

- No Alertmanager: alerts are visible only in Prometheus.
- Nothing deployed to a cloud; the pipeline "deploy" is a docker compose smoke test.
- Telemetry code is copied between services, not packaged as a library.
- Fixed-window rules in the generator; `window` is not fully parameterised.
- Policy gate checks SLO spec and runbook only (no Dockerfile or security checks).
- One runbook, for one failure mode.
- Local load test is single container, so the 800 req/s peak saturates CPU first.
- The rules cache is per replica, so replicas refresh independently.
- Secrets and tokens in docker compose are local-only values.
- No rule unit tests (promtool test) and no dashboard for the pool and cache signals.

## 8. What I would do with one more sprint?

1. Package telemetry as a shared library and add an Alertmanager with routing.
2. Add `promtool test rules` to the pipeline and generate a Grafana dashboard per spec.
3. Build the Azure module and the Front Door edge, and run the load test against
   real replicas to size the pool and replica count.
4. Tail sampling in the collector (keep all error and slow traces), and a synthetic probe
   as a second SLI.
5. Retries with budgets or a circuit breaker for the profile dependency, behind a flag.
6. Long-term metrics store for 28 days compliance reporting and a burn-down view.
7. Policy gate checks for Dockerfile hardening and an SBOM.

## Evidence

Pool exhaustion drill and load tests results.

![alt text](<K6 Load Test Results.png>) ![alt text](<database lock.png>) ![alt text](<Promotions Activity Log.png>) 