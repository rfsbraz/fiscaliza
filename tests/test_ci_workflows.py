"""CI runs on my Homeberry self-hosted runner, with as few GitHub-hosted minutes as possible.

This repo is private, so a hosted job bills Actions minutes. Every job runs on
``[self-hosted, homeberry]``, except the two that need Docker (Backend Tests with its
postgres service, and Docker Build). Those live in ``ci-docker.yml``, which only runs
when backend or Docker files change.
"""

import re
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.y*ml"))
HOMEBERRY = "[self-hosted, homeberry]"
HOSTED_WORKFLOW = "ci-docker.yml"
HOSTED_JOBS = {"backend-test", "docker-build"}


def _jobs(text):
    """Return {job_id: runs-on value or None} for the top-level jobs of a workflow."""
    jobs_block = text.split("\njobs:\n", 1)[1]
    jobs = {}
    current = None
    for line in jobs_block.splitlines():
        header = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if header:
            current = header.group(1)
            jobs[current] = None
            continue
        if re.match(r"^\S", line):
            break
        runs_on = re.match(r"^    runs-on:\s*(.+?)\s*$", line)
        if current and runs_on:
            jobs[current] = runs_on.group(1)
    return jobs


def _triggers(text):
    """Return {event: block text} for the events under the top-level ``on:`` key."""
    on_block = re.search(r"(?ms)^on:\n(.*?)(?=^\S)", text).group(1)
    parts = re.split(r"(?m)^  ([a-z_]+):\s*\n", on_block)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def test_there_are_workflows():
    assert WORKFLOWS


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_jobs_run_on_homeberry_unless_they_need_docker(workflow):
    jobs = _jobs(workflow.read_text())
    assert jobs, f"{workflow.name} has no jobs"
    allowed = HOSTED_JOBS if workflow.name == HOSTED_WORKFLOW else set()
    wrong = {job: runs_on for job, runs_on in jobs.items() if runs_on != HOMEBERRY and job not in allowed}
    assert not wrong, f"{workflow.name}: jobs not on {HOMEBERRY}: {wrong}"


def test_hosted_jobs_only_run_when_backend_or_docker_files_change():
    text = (WORKFLOW_DIR / HOSTED_WORKFLOW).read_text()
    triggers = _triggers(text)
    assert set(triggers) == {"push", "pull_request"}
    for event, block in triggers.items():
        assert re.search(r"(?m)^    paths:\n(      - .+\n)+", block), f"{event} has no paths filter"
        assert "'Dockerfile'" in block and "'app/**'" in block
