# Runbook: <service> - <failure mode>

| | |
|---|---|
| Service | FILL IN |
| Owner / on-call | FILL IN |
| Alert(s) | FILL IN (alert names; the alert's `runbook` annotation links here) |
| Severity | page / ticket |
| Last reviewed | FILL IN (date) |

## What the user sees
One or two sentences: what is broken for customers, and how badly.

## 1. Confirm (first 5 minutes)
- Is the alert real? Check the SLI and the signal behind the alert.
- Scope: all routes or one? Since when? Any deploy or change in the last hour?

## 2. Diagnose
| Signal | Query or command | What it tells you |
|---|---|---|
| FILL IN | FILL IN | FILL IN |

## 3. Mitigate (stop the user impact: fast and reversible)
Numbered steps. For each: the command, the expected effect, and how to undo it.
Say what NOT to do as a first move.

## 4. Fix (stop it happening again)
- Root cause
- Follow-up tickets (owner, due date)

## 5. Verify recovery
Which signals must be back to normal, and for how long, before closing.

## 6. Escalate
Who to call, when, and what to tell them.

## 7. After the incident
- Check the remaining error budget and apply the error budget policy (see README).
- Update this runbook with anything that was missing or wrong.
6b. Filled in for pool exhaustion only

golden-path/runbooks/promotion-api.md (the path your service.toml and the alert annotations already point to):

markdown
# Runbook: promotion-api - database connection pool exhausted

This runbook covers pool exhaustion only. Other failure modes (slow or failing
customer-profile service, bad deploy) are not covered here.

| | |
|---|---|
| Service | promotion-api |
| Owner / on-call | crm |
| Alert(s) | `PromotionApiDbPoolExhausted` (page). `PromotionApiErrorBudgetFastBurn` usually follows it |
| Severity | page |
| Last reviewed | FILL IN (date) |

## What the user sees
Promotion lookups fail with HTTP 503 ("Database busy", `Retry-After: 1`) within
about 200 ms. Each 503 counts against the 99.9% SLO, so budget burns quickly.

## 1. Confirm (first 5 minutes)
1. Prometheus `/alerts`: is `PromotionApiDbPoolExhausted` firing?
2. `sum(rate(db_pool_checkout_timeouts_total{job="promotion-api"}[2m]))` is above 0
   and `db_pool_checked_out{job="promotion-api"}` equals `db_pool_size`.
3. Load or locks? Compare the request rate:
   `sum(rate(http_server_requests_total{job="promotion-api",route="/customers/{customer_id}/promotions"}[1m]))`.
   Near normal (about 60/s) with a full pool means connections are held too long
   (slow queries or locks). Far above normal means load.
4. Any deploy, migration or batch job started in the last hour?

## 2. Diagnose
Look for blocked queries and what is blocking them:

```bash
docker compose exec -T postgres psql -U promotion -d promotions -c \
"SELECT pid, pg_blocking_pids(pid) AS blocked_by, state, wait_event_type,
        now()-query_start AS age, left(query,60) AS query
 FROM pg_stat_activity
 WHERE datname='promotions' AND state <> 'idle'
 ORDER BY query_start;"
```

- Sessions with `wait_event_type = Lock` and a non-empty `blocked_by`: a lock
  problem. The pids in `blocked_by` are the blockers.
- Many short active queries and no blockers: saturation by load or a slow database.
- `rate(rules_cache_stale_served_total[1m])` above 0 means the service is already
  serving cached rules because the rules query is failing.

## 3. Mitigate (fast and reversible)
**A. A lock or long-running query is the cause (what the drill showed):**
1. Identify the blocker from `blocked_by` and its owner (migration, batch job,
   manual session).
2. Cancel it: `SELECT pg_cancel_backend(<pid>);`. If the lock persists, terminate it:
   `SELECT pg_terminate_backend(<pid>);`. Terminating rolls the blocker's
   transaction back, so get the owner's OK first unless customer impact is severe.
3. Expect `db_pool_checked_out` to fall and the 503s to stop within seconds
   (in the drill: FILL IN seconds).

**B. Confirm the service protections are on:**
- `RULES_CACHE_TTL_SECONDS` above 0 (default 30) and `DB_STATEMENT_TIMEOUT_MS`
  above 0 (default 500). If they were overridden, `docker compose up -d promotion-api`
  restores the defaults.

**C. Load is the cause (pool full, no blockers, traffic well above normal):**
- Add replicas. First check `SHOW max_connections;` and make sure
  replicas x (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) stays under it with headroom.

**Do not, as a first move:**
- Raise the pool size: more connections into a blocked database just means more
  blocked sessions, and it can exhaust Postgres itself.
- Restart the service: it empties the rules cache (no stale rules to serve) and
  does not remove the blocker.

## 4. Fix (stop it happening again)
- Find out why the blocker held a lock: migrations must set `lock_timeout`
  (for example 2s) and avoid `ACCESS EXCLUSIVE` locks on tables the service reads.
- Run schema changes and batch jobs off-peak, or against a replica.
- Follow-ups to raise: alert on long-running transactions, size the pool against
  replica count and `max_connections`, load-test at the 800 req/s peak.

## 5. Verify recovery
For 10 minutes: `PromotionApiDbPoolExhausted` resolved, `db_pool_checked_out` below
`db_pool_size`, timeout rate 0, `promotion_api:request_good:ratio_rate5m` above 0.999,
and `rate(rules_cache_stale_served_total[1m])` back to 0.

## 6. Escalate
If the blocker cannot be identified within 15 minutes, or the database itself
looks unhealthy, escalate to the platform team: FILL IN contact.

## 7. After the incident
Check the remaining error budget and apply the error budget policy in the README.

## Evidence from the failure drill
| | Mitigation off | Mitigation on |
|---|---|---|
| Pool alert fired after | -| did not fire (confirm) |
| Fast-burn alert fired after | min=1.44ms | FILL IN |
| Error ratio during the lock | min=1.54ms | FILL IN |
| Recovery after blocker removed | 00:03:12.551891 | n/a |

Dashboards: Prometheus http://localhost:19090, Grafana http://localhost:13000,
Jaeger http://localhost:16686.