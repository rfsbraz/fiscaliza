"""Daily freshness check (.github/scripts/data_freshness.py): parsing health.json and the age threshold.

Nothing here talks to the network: check() gets the body as text.
"""

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("data_freshness", ROOT / ".github" / "scripts" / "data_freshness.py")
data_freshness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_freshness)

TODAY = date(2026, 10, 22)
WORKFLOW = (ROOT / ".github" / "workflows" / "data-freshness.yml").read_text(encoding="utf-8")


def health(source_updated="2026-10-22", status="healthy"):
    return json.dumps(
        {
            "status": status,
            "service": "fiscaliza-api",
            "data": {"tag": "data-2026-10-22", "source_updated": source_updated, "data_commit": "a" * 40},
        }
    )


def test_reads_source_updated():
    assert data_freshness.source_updated(health("2026-10-20")) == date(2026, 10, 20)


@pytest.mark.parametrize("updated, age", [("2026-10-22", 0), ("2026-10-15", 7), ("2026-09-30", 22)])
def test_age_in_days(updated, age):
    assert data_freshness.check(health(updated), TODAY, 7).age == age


@pytest.mark.parametrize("updated, fresh", [("2026-10-22", True), ("2026-10-15", True), ("2026-10-14", False)])
def test_seven_days_is_the_last_fresh_day(updated, fresh):
    assert data_freshness.check(health(updated), TODAY, 7).fresh is fresh


def test_threshold_is_configurable():
    assert data_freshness.check(health("2026-10-10"), TODAY, 14).fresh is True
    assert data_freshness.check(health("2026-10-10"), TODAY, 7).fresh is False


def test_a_date_in_the_future_counts_as_fresh():
    assert data_freshness.check(health("2026-10-23"), TODAY, 7).fresh is True


@pytest.mark.parametrize(
    "body",
    [
        "<!doctype html><title>404</title>",
        json.dumps({"status": "healthy"}),
        json.dumps({"status": "healthy", "data": {"source_updated": None}}),
        json.dumps({"status": "healthy", "data": {"source_updated": "22/10/2026"}}),
        health(status="unhealthy"),
    ],
)
def test_a_bad_or_unhealthy_body_fails(body):
    with pytest.raises(data_freshness.FreshnessError):
        data_freshness.check(body, TODAY, 7)


def test_main_exits_non_zero_when_stale(capsys):
    assert data_freshness.main(["--max-days", "7"], fetch=lambda url: health("2026-10-01"), today=TODAY) == 1
    assert "21" in capsys.readouterr().out


def test_main_exits_zero_when_fresh():
    assert data_freshness.main([], fetch=lambda url: health("2026-10-21"), today=TODAY) == 0


def test_main_exits_non_zero_when_the_fetch_fails():
    def boom(url):
        raise OSError("connection refused")

    assert data_freshness.main([], fetch=boom, today=TODAY) == 1


def test_default_url_is_the_live_health_file():
    assert data_freshness.URL == "https://fiscaliza.pt/api/health.json"


def test_workflow_runs_daily_and_by_hand_read_only():
    assert "schedule:" in WORKFLOW and "cron:" in WORKFLOW
    assert "workflow_dispatch:" in WORKFLOW
    assert "contents: read" in WORKFLOW
    assert "secrets." not in WORKFLOW
    assert ".github/scripts/data_freshness.py" in WORKFLOW


def test_fetch_refuses_a_non_https_url():
    with pytest.raises(OSError):
        data_freshness.fetch("file:///etc/hostname")
