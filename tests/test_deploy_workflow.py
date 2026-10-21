"""The Cloudflare Pages deploy workflow: when it runs, what it runs, and how it treats the token."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def text():
    return WORKFLOW.read_text()


def test_runs_on_push_to_master_daily_and_on_pull_requests():
    t = text()
    assert re.search(r"push:\s*\n\s*branches: \[master\]", t)
    assert re.search(r"pull_request:\s*\n\s*branches: \[master\]", t)
    # Cron is UTC: 06:00 Lisbon in summer time, 05:00 in winter time (docs/DEPLOY.md).
    assert '- cron: "0 5 * * *"' in t


def test_skips_pull_requests_from_forks_and_dependabot():
    t = text()
    assert "github.event.pull_request.head.repo.full_name == github.repository" in t
    assert "github.event.pull_request.user.login != 'dependabot[bot]'" in t


def test_one_deploy_at_a_time_and_none_cancelled():
    t = text()
    block = re.search(r"\nconcurrency:\n((?:  .*\n)+)", t).group(1)
    assert re.search(r"group: [^$\n]+\n", block), "one fixed group, not one per ref"
    assert "${{" not in block
    assert "cancel-in-progress: false" in block


def test_deploys_through_pages_py():
    t = text()
    assert "python -u deploy/pages.py deploy --parlamento-aberto" in t
    assert "--production" in t
    assert "--branch" in t and "github.head_ref" in t


def test_account_is_plain_env_and_the_token_a_secret():
    t = text()
    assert "CLOUDFLARE_ACCOUNT_ID: cda49578092f3bc8595c954e1e771ac1" in t
    assert "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}" in t


def test_never_prints_the_token_or_creates_the_project():
    t = text()
    assert "set -x" not in t
    assert not re.search(r"(echo|printf|cat).*CLOUDFLARE_API_TOKEN", t)
    assert "project create" not in t


def test_builds_the_latest_parlamento_aberto_main():
    # A clone without a checkout: pages.py checks main out once, in its own worktree, so the
    # 2 GB of data is on disk once and not twice.
    clone = re.search(r"git clone [^\n]*", text()).group(0)
    assert "--no-checkout" in clone
    assert "--branch main" in clone
    assert "https://github.com/rfsbraz/parlamento-aberto.git" in clone


def test_wrangler_gets_node_22():
    assert re.search(r"node-version: '22'", text())


def test_deploy_is_time_boxed_and_the_export_capped():
    t = text()
    job = int(re.search(r"\n    timeout-minutes: (\d+)", t).group(1))
    step = int(re.search(r"\n        timeout-minutes: (\d+)", t).group(1))
    assert step < job <= 60
    assert re.search(r"--export-jobs \d", t)
