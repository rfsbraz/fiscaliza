"""Fail when the live data is older than a number of days.

Reads source_updated from https://fiscaliza.pt/api/health.json: the latest date parlamento-aberto
fetched an AR file that changed. It moves when the nightly data PR merges there, the pin moves here
and production deploys, so a stale date means one of those stopped. Used by
.github/workflows/data-freshness.yml; exits 1 so the scheduled run goes red and GitHub sends mail.

    python .github/scripts/data_freshness.py [--url URL] [--max-days N]
"""

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime

URL = "https://fiscaliza.pt/api/health.json"
MAX_DAYS = 7


class FreshnessError(Exception):
    """The body is not a healthy health.json with a source_updated date."""


@dataclass
class Result:
    source_updated: date
    age: int
    fresh: bool


def source_updated(body: str) -> date:
    try:
        health = json.loads(body)
    except ValueError as e:
        raise FreshnessError(f"not JSON: {e}") from e
    if not isinstance(health, dict) or health.get("status") != "healthy":
        raise FreshnessError(f"status is {health.get('status') if isinstance(health, dict) else None!r}")
    value = (health.get("data") or {}).get("source_updated")
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as e:
        raise FreshnessError(f"source_updated is {value!r}") from e


def check(body: str, today: date, max_days: int) -> Result:
    updated = source_updated(body)
    age = (today - updated).days
    return Result(updated, age, age <= max_days)


def fetch(url: str) -> str:
    if not url.startswith("https://"):
        raise OSError(f"not an https URL: {url}")
    headers = {"Accept": "application/json", "User-Agent": "fiscaliza-freshness"}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 (https only, checked above)
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


def main(argv=None, fetch=fetch, today=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=URL)
    parser.add_argument("--max-days", type=int, default=MAX_DAYS)
    args = parser.parse_args(argv)
    today = today or datetime.now(UTC).date()
    try:
        result = check(fetch(args.url), today, args.max_days)
    except (OSError, FreshnessError) as e:
        print(f"::error::{args.url}: {e}")
        return 1
    line = f"source_updated {result.source_updated}, {result.age} days old (limit {args.max_days})"
    if not result.fresh:
        print(f"::error::{line}")
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
