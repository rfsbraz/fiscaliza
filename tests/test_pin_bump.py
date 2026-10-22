"""Automatic data pin moves (#133): deploy/pin_bump.py against fake GitHub and git calls.

Nothing here talks to GitHub or pushes. The fake records every call, so the tests can say what
the script would have pushed, opened, commented or merged.
"""

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "deploy"))
spec = importlib.util.spec_from_file_location("pin_bump", ROOT / "deploy" / "pin_bump.py")
pin_bump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pin_bump)

OLD = "a" * 40
NEW = "b" * 40
HEAD = "c" * 40
PA = "repos/rfsbraz/parlamento-aberto"
REPO = "repos/rfsbraz/parliament"
PIN_TEXT = (
    "# The parlamento-aberto commit Fiscaliza is built from.\n"
    f"commit={OLD}\n"
    "# The data release tag for that commit, empty while there is none.\n"
    "tag=\n"
)
NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def schema(version):
    return f'# Version of the published schema.\nschema_version: "{version}"\n\nmodels:\n'


class FakeGitHub:
    """Answers GET and records writes. routes: {(method, path): response or exception}."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []

    def request(self, method, path, body=None, raw=False):
        self.calls.append((method, path, body))
        key = (method, path)
        if key not in self.routes:
            if method == "GET":
                raise AssertionError(f"unexpected GET {path}")
            return {}
        answer = self.routes[key]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


class FakeGit:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


def compare(status, commits=(), total=None):
    commits = [{"sha": s, "commit": {"message": m}} for s, m in commits]
    return {"status": status, "commits": commits, "total_commits": len(commits) if total is None else total}


@pytest.fixture
def pin_file(tmp_path):
    f = tmp_path / "data-pin"
    f.write_text(PIN_TEXT)
    return f


# Pure helpers


def test_validate_sha_takes_40_hex_only():
    assert pin_bump.validate_sha(NEW.upper()) == NEW
    assert pin_bump.validate_sha(f"  {NEW}\n") == NEW
    for bad in ["", "b" * 39, "b" * 41, "g" * 40, "main", "35b5f08", f"{NEW};rm -rf /"]:
        with pytest.raises(pin_bump.PinBumpError):
            pin_bump.validate_sha(bad)


def test_write_pin_keeps_the_comments_and_clears_the_tag():
    text = PIN_TEXT.replace("tag=\n", "tag=data-2026-10-21\n")
    out = pin_bump.write_pin(text, NEW)
    assert f"commit={NEW}\n" in out and OLD not in out
    assert "tag=\n" in out and "data-2026-10-21" not in out
    assert out.count("#") == PIN_TEXT.count("#")


def test_schema_major():
    assert pin_bump.schema_major(schema("1.2.0")) == 1
    assert pin_bump.schema_major("schema_version: 2.0.0\n") == 2
    assert pin_bump.schema_major("schema_version: '10.1'\n") == 10
    with pytest.raises(pin_bump.PinBumpError):
        pin_bump.schema_major("models: []\n")


def test_schema_guard_only_stops_on_a_major_change():
    assert pin_bump.schema_stop(schema("1.2.0"), schema("1.3.0")) is None
    assert pin_bump.schema_stop(schema("1.2.0"), schema("1.2.0")) is None
    reason = pin_bump.schema_stop(schema("1.2.0"), schema("2.0.0"))
    assert "1.2.0" in reason and "2.0.0" in reason


def test_title_is_a_conventional_commit_with_the_short_sha():
    assert pin_bump.pr_title(NEW) == "chore(data): move the data pin to parlamento-aberto bbbbbbb"


def test_body_lists_both_shas_and_the_commits_in_between():
    body = pin_bump.pr_body(
        OLD,
        NEW,
        compare("ahead", [("1" * 40, "fix(marts): one\n\nlong body"), ("2" * 40, "feat(seeds): two")]),
    )
    assert OLD in body and NEW in body
    assert "- 1111111 fix(marts): one\n" in body
    assert "- 2222222 feat(seeds): two" in body
    assert "long body" not in body
    assert "\u2014" not in body


def test_body_says_when_the_commit_list_is_cut():
    commits = [(f"{i:040x}", f"chore: {i}") for i in range(250)]
    body = pin_bump.pr_body(OLD, NEW, compare("ahead", commits, total=300))
    assert "50 more" in body


# Check evaluation


def run(name, status="completed", conclusion="success", number=1):
    return {"name": name, "status": status, "conclusion": conclusion, "run_number": number, "id": number}


STARTED = NOW - timedelta(minutes=30)


def evaluate(runs, now=NOW):
    return pin_bump.evaluate_runs(runs, ("CI", "Deploy"), started=STARTED, now=now, timeout=timedelta(hours=6))


def test_all_required_workflows_green_is_green():
    assert evaluate([run("CI"), run("Deploy")])[0] == "green"


def test_skipped_and_neutral_count_as_green():
    assert evaluate([run("CI"), run("Deploy", conclusion="skipped"), run("Other", conclusion="neutral")])[0] == "green"


def test_a_missing_or_running_workflow_is_pending():
    assert evaluate([run("CI")])[0] == "pending"
    assert evaluate([run("CI"), run("Deploy", status="in_progress", conclusion=None)])[0] == "pending"
    assert evaluate([])[0] == "pending"


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "action_required", "startup_failure"])
def test_any_bad_conclusion_stops(conclusion):
    state, reason = evaluate([run("CI", conclusion=conclusion), run("Deploy", status="queued", conclusion=None)])
    assert state == "stop"
    assert "CI" in reason and conclusion in reason


def test_any_other_pull_request_workflow_must_pass_too():
    assert evaluate([run("CI"), run("Deploy"), run("Other", conclusion="failure")])[0] == "stop"


def test_only_the_latest_run_of_each_workflow_counts():
    runs = [run("CI", conclusion="failure", number=1), run("CI", number=2), run("Deploy")]
    assert evaluate(runs)[0] == "green"
    runs = [run("CI", number=1), run("CI", conclusion="failure", number=2), run("Deploy")]
    assert evaluate(runs)[0] == "stop"


def test_pending_past_the_timeout_stops():
    late = STARTED + timedelta(hours=6, minutes=1)
    state, reason = evaluate([run("CI"), run("Deploy", status="queued", conclusion=None)], now=late)
    assert state == "stop"
    assert "6 hours" in reason


# bump


def bump_routes(pin_status="ahead", main_status="ahead", old_schema="1.2.0", new_schema="1.3.0", open_prs=()):
    return {
        ("GET", f"{PA}/compare/{NEW}...main"): compare(main_status),
        ("GET", f"{PA}/compare/{OLD}...{NEW}"): compare(pin_status, [("1" * 40, "fix(marts): one")]),
        ("GET", f"{PA}/contents/src/parlamento_aberto/models/schema.yml?ref={OLD}"): schema(old_schema),
        ("GET", f"{PA}/contents/src/parlamento_aberto/models/schema.yml?ref={NEW}"): schema(new_schema),
        ("GET", f"{REPO}/pulls?head=rfsbraz:data/pin-bump&base=master&state=open"): list(open_prs),
        ("POST", f"{REPO}/pulls"): {"number": 140, "html_url": "https://github.com/rfsbraz/parliament/pull/140"},
    }


def do_bump(pin_file, sha=NEW, **routes):
    read, write, git = FakeGitHub(bump_routes(**routes)), FakeGitHub(bump_routes(**routes)), FakeGit()
    result = pin_bump.bump(sha, read=read, write=write, git=git, pin_path=pin_file)
    return result, read, write, git


def test_bump_to_the_current_pin_does_nothing(pin_file):
    result, read, write, git = do_bump(pin_file, sha=OLD)
    assert result == "noop"
    assert git.calls == [] and write.calls == [] and read.writes() == []
    assert pin_file.read_text() == PIN_TEXT


def test_bump_refuses_a_commit_not_on_main(pin_file):
    with pytest.raises(pin_bump.PinBumpError, match="main"):
        do_bump(pin_file, main_status="diverged")


def test_bump_refuses_a_commit_github_does_not_know(pin_file):
    routes = bump_routes()
    routes[("GET", f"{PA}/compare/{NEW}...main")] = pin_bump.NotFound("404")
    read, write, git = FakeGitHub(routes), FakeGitHub(), FakeGit()
    with pytest.raises(pin_bump.PinBumpError, match="not a commit"):
        pin_bump.bump(NEW, read=read, write=write, git=git, pin_path=pin_file)
    assert git.calls == [] and write.calls == []


def test_bump_never_moves_the_pin_backwards(pin_file):
    result, _, write, git = do_bump(pin_file, pin_status="behind")
    assert result == "noop"
    assert git.calls == [] and write.calls == []


def test_bump_resets_the_branch_from_master_and_force_pushes_only_it(pin_file):
    result, _, _, git = do_bump(pin_file)
    assert result == "opened"
    assert git.calls[0] == ("checkout", "-B", "data/pin-bump")
    pushes = [c for c in git.calls if c[0] == "push"]
    assert pushes == [("push", "--force", "origin", "HEAD:refs/heads/data/pin-bump")]
    commit = next(c for c in git.calls if "commit" in c)
    assert "chore(data): move the data pin to parlamento-aberto bbbbbbb" in commit
    assert f"commit={NEW}\n" in pin_file.read_text()


def test_bump_opens_one_pr_with_the_pin_bot(pin_file):
    _, read, write, _ = do_bump(pin_file)
    posts = [c for c in write.writes() if c[1] == f"{REPO}/pulls"]
    assert len(posts) == 1
    body = posts[0][2]
    assert body["head"] == "data/pin-bump" and body["base"] == "master"
    assert body["title"] == "chore(data): move the data pin to parlamento-aberto bbbbbbb"
    assert OLD in body["body"] and NEW in body["body"]
    assert read.writes() == []


def test_bump_edits_the_open_pr_instead_of_opening_another(pin_file):
    result, _, write, _ = do_bump(pin_file, open_prs=[{"number": 139, "html_url": "u"}])
    assert result == "updated"
    assert [c[:2] for c in write.writes()] == [("PATCH", f"{REPO}/pulls/139")]


def test_bump_with_a_schema_major_change_comments_and_fails(pin_file):
    routes = bump_routes(new_schema="2.0.0")
    read, write, git = FakeGitHub(routes), FakeGitHub(routes), FakeGit()
    with pytest.raises(pin_bump.PinBumpError, match="schema"):
        pin_bump.bump(NEW, read=read, write=write, git=git, pin_path=pin_file)
    # The PR is there to look at, with a comment saying why it won't merge.
    assert any(c[0] == "push" for c in git.calls)
    comments = [c for c in read.writes() if c[1] == f"{REPO}/issues/140/comments"]
    assert len(comments) == 1
    assert "2.0.0" in comments[0][2]["body"]


# merge


def merge_routes(files=("deploy/data-pin",), runs=(), head_schema="1.3.0", comments=(), prs=None):
    if prs is None:
        prs = [
            {
                "number": 140,
                "title": "chore(data): move the data pin to parlamento-aberto bbbbbbb",
                "head": {"sha": HEAD},
            }
        ]
    return {
        ("GET", f"{REPO}/pulls?head=rfsbraz:data/pin-bump&base=master&state=open"): prs,
        ("GET", f"{REPO}/issues/140/comments?per_page=100"): list(comments),
        ("GET", f"{REPO}/pulls/140/files?per_page=100"): [{"filename": f} for f in files],
        ("GET", f"{REPO}/contents/deploy/data-pin?ref=master"): PIN_TEXT,
        ("GET", f"{REPO}/contents/deploy/data-pin?ref={HEAD}"): PIN_TEXT.replace(OLD, NEW),
        ("GET", f"{PA}/contents/src/parlamento_aberto/models/schema.yml?ref={OLD}"): schema("1.2.0"),
        ("GET", f"{PA}/contents/src/parlamento_aberto/models/schema.yml?ref={NEW}"): schema(head_schema),
        ("GET", f"{REPO}/actions/runs?head_sha={HEAD}&event=pull_request&per_page=100"): {"workflow_runs": list(runs)},
        ("GET", f"{REPO}/commits/{HEAD}"): {"commit": {"committer": {"date": "2026-10-22T11:30:00Z"}}},
    }


def do_merge(now=NOW, **kw):
    routes = merge_routes(**kw)
    read, write = FakeGitHub(routes), FakeGitHub(routes)
    try:
        return pin_bump.merge(read=read, write=write, now=now), read, write
    except pin_bump.PinBumpError as e:
        e.fakes = (read, write)
        raise


def merges(write):
    return [c for c in write.writes() if c[1] == f"{REPO}/pulls/140/merge"]


def test_merge_with_no_open_pin_pr_does_nothing():
    result, read, write = do_merge(prs=[])
    assert result == "nothing" and write.writes() == [] and read.writes() == []


def test_merge_squashes_when_every_check_is_green():
    result, read, write = do_merge(runs=[run("CI"), run("Deploy")])
    assert result == "merged"
    (call,) = merges(write)
    assert call[0] == "PUT"
    assert call[2]["merge_method"] == "squash"
    assert call[2]["sha"] == HEAD, "only the head the checks ran on"
    assert call[2]["commit_title"] == "chore(data): move the data pin to parlamento-aberto bbbbbbb (#140)"
    assert read.writes() == []


def test_merge_waits_while_checks_run():
    result, read, write = do_merge(runs=[run("CI"), run("Deploy", status="in_progress", conclusion=None)])
    assert result == "pending"
    assert write.writes() == [] and read.writes() == []


def stopped(**kw):
    with pytest.raises(pin_bump.PinBumpError) as info:
        do_merge(**kw)
    read, write = info.value.fakes
    assert merges(write) == []
    comments = [c for c in read.writes() if c[1] == f"{REPO}/issues/140/comments"]
    assert len(comments) == 1
    assert pin_bump.stop_marker(HEAD) in comments[0][2]["body"]
    return str(info.value), comments[0][2]["body"]


def test_merge_stops_on_a_failed_check():
    reason, body = stopped(runs=[run("CI", conclusion="failure"), run("Deploy")])
    assert "CI" in reason and "failure" in body


def test_merge_stops_when_checks_time_out():
    late = NOW + timedelta(hours=6)
    reason, _ = stopped(now=late, runs=[run("CI"), run("Deploy", status="queued", conclusion=None)])
    assert "6 hours" in reason


def test_merge_stops_on_a_schema_major_change():
    reason, _ = stopped(head_schema="2.0.0", runs=[run("CI"), run("Deploy")])
    assert "schema" in reason


def test_merge_stops_when_the_pr_changes_more_than_the_pin():
    reason, _ = stopped(files=("deploy/data-pin", "deploy/pages.py"), runs=[run("CI"), run("Deploy")])
    assert "deploy/pages.py" in reason


def test_merge_refused_by_github_comments_and_fails():
    routes = merge_routes(runs=[run("CI"), run("Deploy")])
    routes[("PUT", f"{REPO}/pulls/140/merge")] = pin_bump.PinBumpError("HTTP 405 Pull Request is not mergeable")
    read, write = FakeGitHub(routes), FakeGitHub(routes)
    with pytest.raises(pin_bump.PinBumpError, match="not mergeable"):
        pin_bump.merge(read=read, write=write, now=NOW)
    comments = [c for c in read.writes() if c[1] == f"{REPO}/issues/140/comments"]
    assert len(comments) == 1 and pin_bump.stop_marker(HEAD) in comments[0][2]["body"]


def test_a_stopped_head_never_merges_later():
    marker = {"body": f"Not merging.\n{pin_bump.stop_marker(HEAD)}"}
    result, read, write = do_merge(runs=[run("CI"), run("Deploy")], comments=[marker])
    assert result == "stopped"
    assert write.writes() == [] and read.writes() == []


def test_a_stop_on_an_older_head_does_not_block_a_new_one():
    marker = {"body": pin_bump.stop_marker("d" * 40)}
    result, _, _ = do_merge(runs=[run("CI"), run("Deploy")], comments=[marker])
    assert result == "merged"


# The command line


def test_missing_pin_bot_token_fails_clearly(monkeypatch, capsys):
    monkeypatch.delenv("PIN_BOT_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    assert pin_bump.main(["merge"]) == 1
    assert "PIN_BOT_TOKEN" in capsys.readouterr().err


def test_never_prints_a_token(monkeypatch, capsys):
    monkeypatch.setenv("PIN_BOT_TOKEN", "secret-value-123")
    monkeypatch.setenv("GITHUB_TOKEN", "other-secret-456")

    def boom(*a, **k):
        raise pin_bump.PinBumpError("stop")

    monkeypatch.setattr(pin_bump, "merge", boom)
    assert pin_bump.main(["merge"]) == 1
    out = capsys.readouterr()
    assert "secret-value-123" not in out.out + out.err
    assert "other-secret-456" not in out.out + out.err
