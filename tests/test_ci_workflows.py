"""CI must run on my Homeberry self-hosted runner, never on GitHub-hosted minutes.

This repo is private, so a hosted job bills Actions minutes. Every job in every
workflow has to say ``runs-on: [self-hosted, homeberry]``.
"""

import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.y*ml"))
HOMEBERRY = "[self-hosted, homeberry]"


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


def test_there_are_workflows():
    assert WORKFLOWS


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_job_runs_on_homeberry(workflow):
    jobs = _jobs(workflow.read_text())
    assert jobs, f"{workflow.name} has no jobs"
    wrong = {job: runs_on for job, runs_on in jobs.items() if runs_on != HOMEBERRY}
    assert not wrong, f"{workflow.name}: jobs not on {HOMEBERRY}: {wrong}"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_runs_terraform(workflow):
    """The old AWS stack and terraform/ are gone, so no job may set up or run Terraform."""
    assert "terraform" not in workflow.read_text().lower()
