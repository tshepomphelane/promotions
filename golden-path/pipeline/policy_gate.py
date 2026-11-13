# Golden-path policy gate
# 
# Fials the pipeline when a service SLO onbording is invalid, stale, or imcomplete

import argparse
import subprocess
import sys
import tempfile
import tomllib 
from pathlib import Path

GENERATOR = Path(__file__).resolve().parents[1] / "slo" / "generate_rules.py"

# SLO latency threshold must be one of the Histogram buckets so the SLI returns data
ALLOWED_LE = {0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path,
                        help="committed generated rules file")
    args = parser.parse_args()

    if not args.spec.is_file():
        print(f"FAIL: SLO spec not found: {args.spec}")
        return 1

    with args.spec.open("rb") as f:
        spec = tomllib.load(f)

    errors: list[str] = []

    # spec and committed rules must be valid and match
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "rules.yml"
        result = subprocess.run(
            [sys.executable, str(GENERATOR), str(args.spec), "--output", str(fresh)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(f"SLO spec invalid: {(result.stdout + result.stderr).strip()}")
        elif not args.rules.is_file():
            errors.append(f"generated rules file missing: {args.rules}")
        elif fresh.read_text() != args.rules.read_text():
            errors.append("committed rules are stale: re-run generate_rules.py and commit")

    # ensure latency threshold matches histogram bucket
    threshold = spec.get("latency_threshold_seconds")
    if threshold not in ALLOWED_LE:
        errors.append(
            f"latency_threshold_seconds={threshold} is not a histogram bucket "
            f"({sorted(ALLOWED_LE)})"
        )

    # runbook must not be empty
    runbook = Path(spec.get("runbook", ""))
    if not runbook.is_file() or runbook.stat().st_size == 0:
        errors.append(f"runbook missing or empty: {runbook}")
    elif "FILL IN" in runbook.read_text(encoding="utf-8"):
        errors.append(f"runbook still contains FILL IN placeholders: {runbook}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("Policy gate passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
