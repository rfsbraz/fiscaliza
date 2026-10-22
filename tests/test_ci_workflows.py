"""Which runner each workflow's jobs use.

CI and Deploy stay on my self-hosted runner until they move to GitHub-hosted runners before
the repo goes public. The data pin workflows are on ``ubuntu-latest`` from the start, so they
need no change at the switch.
"""

import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.y*ml"))
HOMEBERRY = "[self-hosted, homeberry]"
HOSTED = "ubuntu-latest"
ON_HOSTED = {"data-pin-bump.yml", "data-pin-merge.yml"}


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
def test_every_job_runs_on_its_runner(workflow):
    expected = HOSTED if workflow.name in ON_HOSTED else HOMEBERRY
    jobs = _jobs(workflow.read_text())
    assert jobs, f"{workflow.name} has no jobs"
    wrong = {job: runs_on for job, runs_on in jobs.items() if runs_on != expected}
    assert not wrong, f"{workflow.name}: jobs not on {expected}: {wrong}"


@pytest.mark.parametrize("name", sorted(ON_HOSTED))
def test_the_data_pin_workflows_never_mention_a_self_hosted_runner(name):
    text = (WORKFLOWS[0].parent / name).read_text().lower()
    assert "self-hosted" not in text
    assert "homeberry" not in text
