"""Move deploy/data-pin to a new parlamento-aberto commit, and merge the pin PR once CI is green.

    python deploy/pin_bump.py bump --sha SHA   # reset data/pin-bump from master, open or update the PR
    python deploy/pin_bump.py merge            # squash-merge the pin PR when every check is green

Run from .github/workflows/data-pin-bump.yml and data-pin-merge.yml. Needs PIN_BOT_TOKEN (push,
open and merge the PR, so CI and the master Deploy fire) and GITHUB_TOKEN (reads and comments).
See "Automatic pin moves" in docs/DEPLOY.md.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pages  # noqa: E402

API = "https://api.github.com"
PA = "repos/rfsbraz/parlamento-aberto"
REPO = "repos/rfsbraz/fiscaliza"
OWNER = "rfsbraz"
BRANCH = "data/pin-bump"
BASE = "master"
PIN_PATH = "deploy/data-pin"
SCHEMA_PATH = "src/parlamento_aberto/models/schema.yml"
# Every workflow that runs on the pin PR must pass; these two must also have run.
REQUIRED_WORKFLOWS = ("CI", "Deploy")
GREEN = {"success", "skipped", "neutral"}
# A deploy alone takes over half an hour on the runner's single CPU, behind any other queued job.
CHECKS_TIMEOUT = timedelta(hours=6)
AUTHOR = ("Rodrigo Braz", "770716+rfsbraz@users.noreply.github.com")
SHA = re.compile(r"[0-9a-f]{40}")
# The tags parlamento-aberto's data-release.yml publishes: data-<Lisbon date>, then -2, -3 on the same day.
RELEASE_TAG = re.compile(r"data-\d{4}-\d{2}-\d{2}(-\d+)?")


class PinBumpError(Exception):
    """Stop the run and fail the job."""


class NotFound(Exception):
    pass


class GitHub:
    """A small REST client. The token goes in the Authorization header and nowhere else."""

    def __init__(self, token):
        self._token = token

    def request(self, method, path, body=None, raw=False):
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fiscaliza-pin-bump",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{API}/{path}", data=data, headers=headers, method=method)  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                text = resp.read().decode()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(f"{method} {path}: 404") from None
            detail = e.read().decode(errors="replace")[:500]
            raise PinBumpError(f"{method} {path}: HTTP {e.code} {detail}") from None
        if raw:
            return text
        return json.loads(text) if text else {}


def git(*args):
    subprocess.run(["git", *args], check=True)


# Pure helpers


def validate_sha(sha):
    sha = (sha or "").strip().lower()
    if not SHA.fullmatch(sha):
        raise PinBumpError(f"not a full 40 character commit SHA: {sha[:60]!r}")
    return sha


def pin_commit(text):
    for line in text.splitlines():
        key, _, value = line.strip().partition("=")
        if key.strip() == "commit":
            return validate_sha(value)
    raise PinBumpError(f"{PIN_PATH} has no commit= line")


def write_pin(text, sha, tag=None):
    """The pin file with commit= set to sha and tag= set to the data release built from it, or
    emptied when there is none yet (an older tag names another commit)."""
    out = re.sub(r"(?m)^commit=.*$", f"commit={sha}", text)
    return re.sub(r"(?m)^tag=.*$", f"tag={tag or ''}", out)


def release_tag(read, sha):
    """The newest published data release of parlamento-aberto built from sha, or None.

    data-release.yml publishes with --target $GITHUB_SHA, so the release's target_commitish is the
    commit. The tag itself is checked too, so a tag that points elsewhere never lands in the pin."""
    for release in read.request("GET", f"{PA}/releases?per_page=100"):
        tag = release.get("tag_name") or ""
        if release.get("draft") or release.get("prerelease") or not RELEASE_TAG.fullmatch(tag):
            continue
        if release.get("target_commitish") != sha:
            continue
        try:
            if read.request("GET", f"{PA}/commits/{tag}")["sha"] == sha:
                return tag
        except NotFound:
            continue
    return None


def schema_version(text):
    m = re.search(r"""(?m)^schema_version:\s*["']?([0-9][^"'\s]*)""", text)
    if not m:
        raise PinBumpError(f"no schema_version in {SCHEMA_PATH}")
    return m.group(1)


def schema_major(text):
    return int(schema_version(text).split(".")[0])


def schema_stop(old_text, new_text):
    """Why not to merge when the schema major changed, or None."""
    if schema_major(old_text) == schema_major(new_text):
        return None
    return (
        f"the parlamento-aberto schema_version goes from {schema_version(old_text)} to "
        f"{schema_version(new_text)}, a new major version. Fiscaliza's sync and export need checking "
        "against the new schema before this pin moves."
    )


def _hours(delta):
    return int(delta.total_seconds() // 3600)


def pr_title(new):
    return f"chore(data): move the data pin to parlamento-aberto {new[:7]}"


def tag_title(tag):
    return f"chore(data): pin the data release {tag}"


def tag_body(sha, tag):
    url = "https://github.com/rfsbraz/parlamento-aberto"
    return (
        f"Sets `tag={tag}` in `deploy/data-pin`. The pinned commit [`{sha}`]({url}/commit/{sha}) is unchanged; "
        f"its data release is now published: {url}/releases/tag/{tag}\n\n"
        "With the tag in the pin, the deploy syncs that release from GitHub instead of building the pin "
        "locally, and the download page (/dados) links its files.\n\n"
        "## Merge\n\n"
        "This PR was opened by the pin workflow (`data-pin-bump.yml`). `data-pin-merge.yml` squash-merges "
        "it once every check on this head is green.\n"
    )


def pr_body(old, new, cmp):
    url = "https://github.com/rfsbraz/parlamento-aberto"
    lines = [
        "Moves `deploy/data-pin` to the latest parlamento-aberto `main`.",
        "",
        f"- Old pin: [`{old}`]({url}/commit/{old})",
        f"- New pin: [`{new}`]({url}/commit/{new})",
        f"- Diff: {url}/compare/{old[:12]}...{new[:12]}",
        "",
        f"## parlamento-aberto commits ({cmp.get('total_commits', len(cmp['commits']))})",
        "",
    ]
    for c in cmp["commits"]:
        subject = c["commit"]["message"].splitlines()[0]
        lines.append(f"- {c['sha'][:7]} {subject}")
    more = cmp.get("total_commits", 0) - len(cmp["commits"])
    if more > 0:
        lines.append(f"- and {more} more, see the diff link")
    lines += [
        "",
        "## Merge",
        "",
        "This PR was opened by the pin workflow (`data-pin-bump.yml`). `data-pin-merge.yml` squash-merges "
        "it once every check on this head is green. It leaves it open with a comment if a check fails, "
        f"the checks take over {_hours(CHECKS_TIMEOUT)} hours, or the "
        "schema major version changes. A newer parlamento-aberto commit replaces this head.",
    ]
    return "\n".join(lines) + "\n"


def stop_marker(sha):
    return f"<!-- pin-bump-stop:{sha} -->"


def evaluate_runs(runs, required, started, now, timeout):
    """("green" | "pending" | "stop", reason) for the workflow runs on the PR head."""
    latest = {}
    for r in runs:
        key = r["name"]
        if key not in latest or (r["run_number"], r["id"]) > (latest[key]["run_number"], latest[key]["id"]):
            latest[key] = r
    for name, r in sorted(latest.items()):
        if r["status"] == "completed" and r["conclusion"] not in GREEN:
            return "stop", f"the {name} workflow finished with conclusion {r['conclusion']}"
    waiting = sorted(n for n, r in latest.items() if r["status"] != "completed")
    waiting += sorted(n for n in required if n not in latest)
    if waiting:
        if now - started > timeout:
            return "stop", f"{', '.join(waiting)} did not finish within {_hours(timeout)} hours"
        return "pending", f"waiting for {', '.join(waiting)}"
    return "green", "every workflow on this head passed"


# GitHub reads


def _schema_at(read, sha):
    try:
        return read.request("GET", f"{PA}/contents/{SCHEMA_PATH}?ref={sha}", raw=True)
    except NotFound:
        raise PinBumpError(f"parlamento-aberto {sha[:7]} has no {SCHEMA_PATH}") from None


def _open_pr(read):
    prs = read.request("GET", f"{REPO}/pulls?head={OWNER}:{BRANCH}&base={BASE}&state=open")
    return prs[0] if prs else None


def _comment(read, number, body):
    read.request("POST", f"{REPO}/issues/{number}/comments", {"body": body})


# bump


def bump(sha, read, write, git=git, pin_path=pages.PIN_FILE):
    """Move the pin on data/pin-bump to sha and open or update the pin PR. Returns what it did."""
    new = validate_sha(sha)
    pin = pages.read_pin(pin_path)
    old = pin.commit
    if new == old:
        # The dispatch can come before the release is published; a later one for the same
        # commit fills in the tag.
        tag = release_tag(read, new)
        if not tag or tag == pin.tag:
            print(f"The pin on {BASE} is already {new}{f' ({pin.tag})' if pin.tag else ''}. Nothing to do.")
            return "noop"
        result, number = _push_and_open(read, write, git, Path(pin_path), new, tag, tag_title(tag), tag_body(new, tag))
        print(f"Pin PR #{number} {result}: {new[:7]} gets its release tag {tag}.")
        return result

    try:
        on_main = read.request("GET", f"{PA}/compare/{new}...main")
    except NotFound:
        raise PinBumpError(f"{new} is not a commit in parlamento-aberto") from None
    if on_main["status"] not in ("identical", "ahead"):
        raise PinBumpError(f"{new} is not on parlamento-aberto main (compare status {on_main['status']})")

    cmp = read.request("GET", f"{PA}/compare/{old}...{new}")
    if cmp["status"] in ("behind", "identical"):
        print(f"{new} is not newer than the pin {old}. Nothing to do.")
        return "noop"
    if cmp["status"] != "ahead":
        raise PinBumpError(f"{new} and the pin {old} have diverged (compare status {cmp['status']})")

    tag = release_tag(read, new)
    result, number = _push_and_open(read, write, git, Path(pin_path), new, tag, pr_title(new), pr_body(old, new, cmp))
    print(f"Pin PR #{number} {result}: {old[:7]} to {new[:7]}{f' ({tag})' if tag else ''}.")

    reason = schema_stop(_schema_at(read, old), _schema_at(read, new))
    if reason:
        _comment(read, number, f"Not merging automatically: {reason}\n\nI'll check it and merge by hand.")
        raise PinBumpError(f"PR #{number}: {reason}")
    return result


def _push_and_open(read, write, git, path, sha, tag, title, body):
    """Commit the pin on data/pin-bump, push it and open or update the pin PR."""
    git("checkout", "-B", BRANCH)
    path.write_text(write_pin(path.read_text(), sha, tag))
    name, email = AUTHOR
    git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "--quiet", "-m", title, "--", str(path))
    # The only force-push anywhere: data/pin-bump is rebuilt from master on every move.
    git("push", "--force", "origin", f"HEAD:refs/heads/{BRANCH}")
    pr = _open_pr(read)
    if pr:
        write.request("PATCH", f"{REPO}/pulls/{pr['number']}", {"title": title, "body": body})
        return "updated", pr["number"]
    pr = write.request("POST", f"{REPO}/pulls", {"title": title, "body": body, "head": BRANCH, "base": BASE})
    return "opened", pr["number"]


# merge


def merge(read, write, now=None):
    """Squash-merge the open pin PR if every check on its head passed. Returns what it did."""
    now = now or datetime.now(UTC)
    pr = _open_pr(read)
    if not pr:
        print("No open pin PR.")
        return "nothing"
    number, head = pr["number"], pr["head"]["sha"]
    marker = stop_marker(head)
    comments = read.request("GET", f"{REPO}/issues/{number}/comments?per_page=100")
    if any(marker in (c.get("body") or "") for c in comments):
        print(f"PR #{number} was already stopped at {head[:7]}. It waits for me or for a newer pin.")
        return "stopped"

    def stop(reason):
        _comment(read, number, f"Not merging automatically: {reason}\n\nI'll check it and merge by hand.\n{marker}")
        raise PinBumpError(f"PR #{number}: {reason}")

    files = [f["filename"] for f in read.request("GET", f"{REPO}/pulls/{number}/files?per_page=100")]
    if files != [PIN_PATH]:
        stop(f"it changes more than {PIN_PATH}: {', '.join(files)}")

    old = pin_commit(read.request("GET", f"{REPO}/contents/{PIN_PATH}?ref={BASE}", raw=True))
    new = pin_commit(read.request("GET", f"{REPO}/contents/{PIN_PATH}?ref={head}", raw=True))
    reason = schema_stop(_schema_at(read, old), _schema_at(read, new))
    if reason:
        stop(reason)

    runs = read.request("GET", f"{REPO}/actions/runs?head_sha={head}&event=pull_request&per_page=100")
    date = read.request("GET", f"{REPO}/commits/{head}")["commit"]["committer"]["date"]
    started = datetime.fromisoformat(date.replace("Z", "+00:00"))
    state, why = evaluate_runs(runs["workflow_runs"], REQUIRED_WORKFLOWS, started, now, CHECKS_TIMEOUT)
    if state == "pending":
        print(f"PR #{number}: {why}.")
        return "pending"
    if state == "stop":
        stop(why)

    try:
        write.request(
            "PUT",
            f"{REPO}/pulls/{number}/merge",
            {
                "merge_method": "squash",
                "sha": head,
                "commit_title": f"{pr['title']} (#{number})",
                "commit_message": f"parlamento-aberto {old[:12]} to {new[:12]}.",
            },
        )
    except (PinBumpError, NotFound) as e:
        stop(f"GitHub refused the merge: {e}")
    print(f"PR #{number} squash-merged at {head[:7]}.")
    return "merged"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("bump")
    p.add_argument("--sha", required=True)
    sub.add_parser("merge")
    args = parser.parse_args(argv)

    bot = os.environ.get("PIN_BOT_TOKEN", "")
    if not bot:
        print(
            "PIN_BOT_TOKEN is not set. Add it in Settings, Secrets and variables, Actions: a fine-grained token "
            "for rfsbraz/fiscaliza only, with Contents and Pull requests read and write (docs/DEPLOY.md).",
            file=sys.stderr,
        )
        return 1
    read = GitHub(os.environ.get("GITHUB_TOKEN") or bot)
    write = GitHub(bot)
    try:
        if args.command == "bump":
            bump(args.sha, read=read, write=write)
        else:
            merge(read=read, write=write)
    except (PinBumpError, NotFound, subprocess.CalledProcessError) as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
