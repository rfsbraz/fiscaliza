"""Every job runs on a GitHub-hosted runner, never on a self-hosted one.

The repo is public, so a pull request from a fork runs CI with its own code. On a self-hosted
runner that code would run on a persistent machine that also runs the production deploy, so
every job in every workflow has to say ``runs-on: ubuntu-latest``.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
HOSTED = "ubuntu-latest"


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
def test_every_job_runs_on_a_github_hosted_runner(workflow):
    jobs = _jobs(workflow.read_text())
    assert jobs, f"{workflow.name} has no jobs"
    wrong = {job: runs_on for job, runs_on in jobs.items() if runs_on != HOSTED}
    assert not wrong, f"{workflow.name}: jobs not on {HOSTED}: {wrong}"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_mentions_a_self_hosted_runner(workflow):
    text = workflow.read_text().lower()
    assert "self-hosted" not in text
    assert "homeberry" not in text


def test_actionlint_declares_no_self_hosted_labels():
    config = ROOT / ".github" / "actionlint.yaml"
    assert not config.exists() or "self-hosted-runner" not in config.read_text()


def test_deploy_logs_print_nothing_about_the_machine():
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    for probe in ("nproc", "free -h", "df -h"):
        assert probe not in deploy


@pytest.mark.parametrize("doc", ["docs/DEPLOY.md", "README.md", "CONTRIBUTING.md"])
def test_docs_do_not_describe_a_self_hosted_runner(doc):
    text = (ROOT / doc).read_text().lower()
    assert "homeberry" not in text
    assert "self-hosted" not in text
    assert "my single runner" not in text
