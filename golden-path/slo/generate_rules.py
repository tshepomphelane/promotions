#!/usr/bin/env python3

# Generate Prometheus SLO recording rules, multi-window burn-rate alerts and
# basic health alerts from a single service spec (service.toml).

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


def ratio_expression(spec: dict[str, object], period: str) -> str:
    labels = f'job="{spec["job"]}", route="{spec["route"]}"'
    good_labels = (
        f'{labels}, '
        f'status_code!~"5..", '
        f'le="{spec["latency_threshold_seconds"]}"'
    )

    return (
        f"sum(rate("
        f"http_server_request_duration_seconds_bucket"
        f"{{{good_labels}}}[{period}])) "
        f"/ sum(rate("
        f"http_server_requests_total"
        f"{{{labels}}}[{period}]))"
    )


def burn_expression(
    service: str,
    period: str,
    budget: float,
    burn_rate: float,
) -> str:
    return (
        f"(1 - {service}:request_good:ratio_rate{period}) "
        f"> {burn_rate * budget:.7f}"
    )


def alert(
    spec: dict[str, object],
    name: str,
    expr: str,
    duration: str,
    severity: str,
    summary: str,
    description: str,
) -> list[str]:
    return [
        f"      - alert: {name}",
        f"        expr: {expr}",
        f"        for: {duration}",
        "        labels:",
        f"          severity: {severity}",
        f"          service: {spec['service']}",
        f"          owner: {spec['owner']}",
        "        annotations:",
        f'          summary: "{summary}"',
        f'          description: "{description}"',
        f"          runbook: {spec['runbook']}",
    ]


def generate(spec: dict[str, object]) -> str:
    name = str(spec["service"])
    service = name.replace("-", "_")
    pascal = service.title().replace("_", "")
    job = str(spec["job"])
    budget = 1 - float(spec["target"])

    page_short = burn_expression(service, "5m", budget, 14.4)
    page_long = burn_expression(service, "1h", budget, 14.4)
    ticket_short = burn_expression(service, "30m", budget, 6)
    ticket_long = burn_expression(service, "6h", budget, 6)

    lines = [
        "groups:",
        f"  - name: {service}-slo",
        "    rules:",
    ]

    for period in ("5m", "30m", "1h", "6h"):
        lines.extend(
            [
                f"      - record: {service}:request_good:ratio_rate{period}",
                f"        expr: {ratio_expression(spec, period)}",
            ]
        )

    # Multi-window burn-rate alerts
    lines += alert(
        spec,
        f"{pascal}ErrorBudgetFastBurn",
        f"({page_short}) and ({page_long})",
        "2m",
        "page",
        f"{name} is rapidly consuming its error budget",
        "The 5m and 1h burn rates exceed 14.4x the 28-day error budget. "
        "This consumes 2% of the budget in about one hour.",
    )
    lines += alert(
        spec,
        f"{pascal}ErrorBudgetSlowBurn",
        f"({ticket_short}) and ({ticket_long})",
        "15m",
        "ticket",
        f"{name} is steadily consuming its error budget",
        "The 30m and 6h burn rates exceed 6x the 28-day error budget. "
        "This consumes 5% of the budget in about six hours.",
    )

    # Total outage: no traffic means the ratios above return no data,
    # so alert on the scrape itself.
    lines += alert(
        spec,
        f"{pascal}Down",
        f'up{{job="{job}"}} == 0 or absent(up{{job="{job}"}})',
        "2m",
        "page",
        f"{name} is down or not being scraped",
        "Prometheus cannot scrape the service, so the SLO alerts have no data. "
        "Check the service and the scrape limits.",
    )

    # Opt-in saturation alert for services that export db_pool_* metrics.
    if spec.get("db_pool", False):
        lines += alert(
            spec,
            f"{pascal}DbPoolExhausted",
            f'sum(rate(db_pool_checkout_timeouts_total{{job="{job}"}}[2m])) > 0',
            "1m",
            "page",
            f"{name} cannot get database connections",
            "Requests are failing because no database connection became free "
            "within the pool timeout. Connections are being held too long by "
            "slow queries or locks.",
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with args.spec.open("rb") as spec_file:
        spec = tomllib.load(spec_file)

    required = {
        "service",
        "job",
        "route",
        "target",
        "window",
        "latency_threshold_seconds",
        "owner",
        "runbook",
    }

    missing = required - spec.keys()

    if missing:
        raise SystemExit(
            f"Missing required SLO fields: {', '.join(sorted(missing))}"
        )

    if not 0 < float(spec["target"]) < 1:
        raise SystemExit("target must be between 0 and 1")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(spec), encoding="utf-8")


if __name__ == "__main__":
    main()