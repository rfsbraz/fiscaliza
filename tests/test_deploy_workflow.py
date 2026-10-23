"""The Cloudflare Pages deploy workflow: when it runs, what it runs, and how it treats the token."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def text():
    return WORKFLOW.read_text()


def test_runs_on_push_to_master_and_on_pull_requests_only():
    t = text()
    assert re.search(r"push:\s*\n\s*branches: \[master\]", t)
    assert re.search(r"pull_request:\s*\n\s*branches: \[master\]", t)
    # The data only changes when a PR moves deploy/data-pin, so there is no schedule.
    assert "schedule:" not in t
    assert "cron" not in t


def test_skips_pull_requests_from_forks_and_dependabot():
    t = text()
    assert "github.event.pull_request.head.repo.full_name == github.repository" in t
    assert "github.event.pull_request.user.login != 'dependabot[bot]'" in t


def concurrency_block():
    t = text()
    # On the deploy job, not the workflow: a run the changes job skips then never queues.
    assert "\nconcurrency:" not in t
    changes, deploy = re.search(r"\n  changes:\n(.*)\n  deploy:\n(.*)", t, re.S).groups()
    assert "concurrency:" not in changes
    return re.search(r"\n    concurrency:\n((?:      .*\n)+)", deploy).group(1)


def test_previews_and_production_never_share_a_concurrency_group():
    # One group for every trigger kept a single pending deploy, so each push to master cancelled
    # the queued previews and a preview could cancel a queued production deploy.
    block = concurrency_block()
    assert "pages-deploy\n" not in block
    group = re.search(r"group: (.*)\n", block).group(1)
    assert group == (
        "${{ github.event_name == 'pull_request' && "
        "format('pages-preview-{0}', github.event.pull_request.number) || 'pages-production' }}"
    )


def test_a_newer_push_cancels_a_preview_but_never_a_production_deploy():
    block = concurrency_block()
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n" in block


def test_the_workflow_keeps_the_name_the_pin_merge_waits_for():
    # data-pin-merge.yml listens to the Deploy workflow by name and pin_bump.py requires a run
    # called Deploy on the pin PR head.
    assert text().startswith("name: Deploy\n")
    merge = (ROOT / ".github" / "workflows" / "data-pin-merge.yml").read_text()
    assert "workflows: [CI, Deploy, gitleaks]" in merge
    assert 'REQUIRED_WORKFLOWS = ("CI", "Deploy")' in (ROOT / "deploy" / "pin_bump.py").read_text()


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


def test_clones_parlamento_aberto_without_a_checkout():
    # pages.py checks the pin out once, in its own worktree, so the 2 GB of data is on disk
    # once and not twice. It fetches the pinned SHA itself when main has moved past it.
    clone = re.search(r"git clone [^\n]*", text()).group(0)
    assert "--no-checkout" in clone
    assert "https://github.com/rfsbraz/parlamento-aberto.git" in clone


def test_wrangler_gets_node_22():
    assert re.search(r"node-version: '22'", text())


def test_deploy_is_time_boxed_and_the_export_capped():
    t = text().split("\n  deploy:\n", 1)[1]
    job = int(re.search(r"\n    timeout-minutes: (\d+)", t).group(1))
    step = int(re.search(r"\n        timeout-minutes: (\d+)", t).group(1))
    assert (step, job) == (80, 90)
    # The export takes its workers from the cgroup CPU limit (cpu.max) or the CPU count, so
    # whatever runner it lands on applies without a hardcoded count.
    assert "EXPORT_WORKERS" not in t


def preview_paths():
    """The ERE the changes job matches each changed file against."""
    return re.compile(re.search(r"PREVIEW_PATHS: '([^']+)'", text()).group(1))


def test_pull_requests_also_trigger_on_labeled():
    assert re.search(
        r"pull_request:\s*\n\s*branches: \[master\]\s*\n\s*types: \[opened, synchronize, reopened, labeled\]",
        text(),
    )


def test_only_site_paths_need_a_preview():
    pattern = preview_paths()
    for path in [
        "frontend/src/App.jsx",
        "fiscaliza_data/export.py",
        "app/main.py",
        "deploy/pages.py",
        "deploy/data-pin",
        ".github/workflows/deploy.yml",
    ]:
        assert pattern.search(path), path
    for path in [
        "README.md",
        "docs/DEPLOY.md",
        "tests/test_deploy_workflow.py",
        ".github/workflows/ci.yml",
        "scripts/frontend/x.py",
        "myapp/main.py",
    ]:
        assert not pattern.search(path), path


def test_the_preview_label_forces_a_preview_and_other_labels_start_nothing():
    t = text()
    # Adding some other label must not even start the changes job.
    assert "github.event.action != 'labeled' || github.event.label.name == 'preview'" in t
    assert "contains(github.event.pull_request.labels.*.name, 'preview')" in t


def test_deploy_waits_for_the_changes_job_on_pull_requests_only():
    t = text()
    deploy = t.split("\n  deploy:\n", 1)[1]
    assert "needs: changes" in deploy
    assert "github.event_name == 'push'" in deploy
    assert "needs.changes.outputs.preview == 'true'" in deploy


def deploy_step_env():
    t = text()
    step = t[t.index("- name: Deploy\n") :]
    return step[: step.index("run:")]


def test_the_build_gets_the_public_sentry_dsn_and_its_environment():
    # deploy/pages.py runs npm run build with the step's env, so Vite inlines VITE_* there.
    env = deploy_step_env()
    assert re.search(r"^\s+VITE_SENTRY_DSN: ", env, re.M)
    assert "VITE_SENTRY_ENVIRONMENT: ${{ github.event_name == 'push' && 'production' || 'preview' }}" in env
    # The DSN is public; no Sentry auth token goes into the build.
    assert "SENTRY_AUTH_TOKEN" not in text()
