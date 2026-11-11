#!/usr/bin/env python3

# generate Promotheus SLO recording and multi window burn rate alert rules

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

def generate(spec: dict[str, object]) -> str:
    service = str(spec["service"]).replace("-", "_")
    budget = 1 - float(spec["target"])
    owner = str(spec["owner"])
    runbook = str(spec["runbook"])

    page_short = burn_expression(service, "5m", budget, 14.4)
    page_long = burn_expression(service, "1h", budget, 14.4)

    ticket_short = burn_expression(service, "30m", budget, 6)
    ticket_long = burn_expression(service, "6h", budget, 6)

    fast_alert = f"{service.title().replace('_', '')}ErrorBudgetFastBurn"
    slow_alert = f"{service.title().replace('_', '')}ErrorBudgetSlowBurn"

    lines = [
        "groups:",
        f"  - name: {service}-slo",
        "    rules:",
    ]

    for period in ("5m", "30m", "1h", "6h"):
        lines.extend(
            [
                f" - record: {service}:request_good:ratio_rate{period}",
                f" expr: {ratio_expression(spec, period)}",
            ]
        )
    lines.extend(
        [
            f"      - alert: {fast_alert}",
            f"        expr: ({page_short}) and ({page_long})",
            "        for: 2m",
            "        labels:",
            "          severity: page",
            f"          service: {spec['service']}",
            f"          owner: {owner}",
            "        annotations:",
            f'          summary: "{spec["service"]} is rapidly consuming its error budget"',
            '          description: "The 5m and 1h burn rates exceed 14.4x the 28-day error budget. This consumes 2% of the budget in about one hour."',
            f"          runbook: {runbook}",
            f"      - alert: {slow_alert}",
            f"        expr: ({ticket_short}) and ({ticket_long})",
            "        for: 15m",
            "        labels:",
            "          severity: ticket",
            f"          service: {spec['service']}",
            f"          owner: {owner}",
            "        annotations:",
            f'          summary: "{spec["service"]} is steadily consuming its error budget"',
            '          description: "The 30m and 6h burn rates exceed 6x the 28-day error budget. This consumes 5% of the budget in about six hours."',
            f"          runbook: {runbook}",
        ]
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
    