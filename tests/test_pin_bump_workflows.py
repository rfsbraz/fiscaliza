"""The automatic pin move workflows (#133): what starts them, which token does what, and where they run."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUMP = ROOT / ".github" / "workflows" / "data-pin-bump.yml"
MERGE = ROOT / ".github" / "workflows" / "data-pin-merge.yml"


def run_blocks(text):
    """The body of every `run: |` block and every one-line `run:`."""
    blocks = re.findall(r"\n(\s+)run: \|\n((?:\1  .*\n|\s*\n)+)", text)
    return [b for _, b in blocks] + re.findall(r"run: (?!\|)(.+)", text)


def test_bump_starts_on_the_dispatch_and_by_hand_only():
    t = BUMP.read_text()
    assert re.search(r"repository_dispatch:\n\s+types: \[data-updated\]", t)
    assert re.search(r"workflow_dispatch:\n\s+inputs:\n\s+sha:", t)
    for trigger in ("push:", "pull_request", "schedule:", "workflow_run:"):
        assert trigger not in t


def test_a_newer_bump_cancels_an_older_one():
    t = BUMP.read_text()
    assert re.search(r"\nconcurrency:\n  group: data-pin-bump\n  cancel-in-progress: true\n", t)


def test_merge_runs_when_ci_or_deploy_finish_on_the_pin_branch_only():
    t = MERGE.read_text()
    assert re.search(r"workflow_run:\n\s+workflows: \[CI, Deploy\]\n\s+types: \[completed\]", t)
    assert "github.event.workflow_run.head_branch == 'data/pin-bump'" in t
    assert "github.event.workflow_run.event == 'pull_request'" in t
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in t
    # One at a time and never cancelled: two runs finishing together must not both merge.
    assert re.search(r"\nconcurrency:\n  group: data-pin-merge\n  cancel-in-progress: false\n", t)


def test_merge_never_waits_on_the_runner():
    # One runner: a job that sat waiting for CI would hold the runner CI needs.
    t = MERGE.read_text()
    assert "sleep" not in t
    assert int(re.search(r"timeout-minutes: (\d+)", t).group(1)) <= 10


def test_both_run_the_script_with_the_pin_bot_token():
    for path, command in [
        (BUMP, 'python deploy/pin_bump.py bump --sha "$SHA"'),
        (MERGE, "python deploy/pin_bump.py merge"),
    ]:
        t = path.read_text()
        assert command in t
        assert "PIN_BOT_TOKEN: ${{ secrets.PIN_BOT_TOKEN }}" in t
        assert "GITHUB_TOKEN: ${{ github.token }}" in t


def test_a_missing_pin_bot_token_fails_before_anything_else():
    for path in (BUMP, MERGE):
        t = path.read_text()
        check = t.index("Check PIN_BOT_TOKEN")
        assert check < t.index("actions/checkout")
        assert "::error::PIN_BOT_TOKEN is not set" in t


def test_secrets_and_event_values_never_reach_a_shell_line():
    for path in (BUMP, MERGE):
        assert len(run_blocks(path.read_text())) == 2
        for block in run_blocks(path.read_text()):
            assert "${{" not in block, f"{path.name}: pass values through env, not into the script"
        t = path.read_text()
        assert "set -x" not in t
        assert not re.search(r"(echo|printf|cat)[^\n]*\$PIN_BOT_TOKEN", t)


def test_only_the_bump_checks_out_with_push_credentials():
    bump = BUMP.read_text()
    assert "token: ${{ secrets.PIN_BOT_TOKEN }}" in bump
    assert "ref: master" in bump
    merge = MERGE.read_text()
    assert "persist-credentials: false" in merge
    assert "ref: master" in merge


def test_github_token_gets_only_what_the_reads_and_comments_need():
    bump = BUMP.read_text()
    assert re.search(r"\npermissions:\n  contents: read\n  pull-requests: write\n\n", bump)
    merge = MERGE.read_text()
    assert re.search(r"\npermissions:\n  actions: read\n  contents: read\n  pull-requests: write\n\n", merge)
