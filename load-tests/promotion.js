import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://promotion-api:8000';
const SCENARIO = __ENV.SCENARIO || 'steady';
const DURATION = __ENV.DURATION || '2m';

// 403 (inactive customer) & 404 (unknown customer) are valid answers,
// not failures, and they count as good events in the SLO.
http.setResponseCallback(http.expectedStatuses(200, 403, 404));

// Mostly eligible customers, some inactive, a few unknown.
function pickCustomer() {
  const r = Math.random();
  if (r < 0.7) return Math.random() < 0.5 ? 'CUST-001' : 'CUST-003';
  if (r < 0.9) return 'CUST-002';
  return 'CUST-999';
}

// 403 (inactive customer) and 404 (unknown customer) are valid answers,
// not failures, and they count as good events in the SLO.
http.setResponseCallback(http.expectedStatuses(200, 403, 404));

// Mostly eligible customers, some inactive, a few unknown.
function pickCustomer() {
  const r = Math.random();
  if (r < 0.7) return Math.random() < 0.5 ? 'CUST-001' : 'CUST-003';
  if (r < 0.9) return 'CUST-002';
  return 'CUST-999';
}

const scenarios = {
  // Normal traffic: ~60 req/s
  steady: {
    executor: 'constant-arrival-rate',
    rate: 60,
    timeUnit: '1s',
    duration: DURATION,
    preAllocatedVUs: 50,
    maxVUs: 300,
  },
  // Friday 18:00 promotional email: ramp to ~800 req/s, hold, ramp down
  peak: {
    executor: 'ramping-arrival-rate',
    startRate: 60,
    timeUnit: '1s',
    preAllocatedVUs: 400,
    maxVUs: 1500,
    stages: [
      { target: 800, duration: '1m' },
      { target: 800, duration: DURATION },
      { target: 60, duration: '1m' },
    ],
  },
};

export const options = {
  scenarios: { load: scenarios[SCENARIO] },
  // Mirrors the SLO: 99.9% of requests succeed and finish within 300 ms
  thresholds: {
    http_req_failed: ['rate<0.001'],
    http_req_duration: ['p(99.9)<300'],
  },
};

export default function () {
  const res = http.get(
    `${BASE_URL}/customers/${pickCustomer()}/promotions`,
    { tags: { name: 'promotions' } } // group by route, not by customer id
  );
  check(res, { 'status is 200, 403 or 404': (r) => [200, 403, 404].includes(r.status) });
}