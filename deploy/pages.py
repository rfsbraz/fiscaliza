"""Build Fiscaliza from the pinned parlamento-aberto commit and upload it to Cloudflare Pages.

    python deploy/pages.py deploy --parlamento-aberto PATH   # build the release from the pin
    python deploy/pages.py deploy --release DIR              # a release folder built from the pin
    python deploy/pages.py deploy ... --branch NAME          # preview branch (default: preview)
    python deploy/pages.py deploy ... --production           # production (master)
    python deploy/pages.py deploy ... --dry-run              # print the steps, run nothing
    python deploy/pages.py prepare DIST                      # only the Pages step on a built dist/

See docs/DEPLOY.md.
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
FRONTEND = ROOT / "frontend"
PIN_FILE = DEPLOY / "data-pin"
HEADERS_FILE = DEPLOY / "_headers"

PROJECT = "fiscaliza"
PRODUCTION_BRANCH = "master"
PREVIEW_BRANCH = "preview"
# Cloudflare Pages limits per deployment (free plan).
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024
# Wrangler 4 needs Node 22 or newer.
DEFAULT_WRANGLER = "npx --yes wrangler@4.151.3"


class DeployError(Exception):
    pass


@dataclass
class Step:
    name: str
    argv: list[str]
    cwd: Path = ROOT
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Pin:
    commit: str
    tag: str | None


def read_pin(path=PIN_FILE):
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    commit = values.get("commit", "")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise DeployError(f"{path}: commit must be a full 40 character SHA, got {commit!r}")
    return Pin(commit=commit, tag=values.get("tag") or None)


def _git(checkout, *args):
    return subprocess.run(["git", "-C", str(checkout), *args], check=True, capture_output=True, text=True)


def fetch_pin(checkout, commit):
    """Make sure the pinned commit is in the parlamento-aberto clone, whatever its branches
    point at. Fetches that exact SHA when it is missing, one commit deep in a shallow clone."""
    try:
        _git(checkout, "rev-parse", "--git-dir")
    except subprocess.CalledProcessError as e:
        raise DeployError(f"{checkout} is not a parlamento-aberto git clone") from e
    try:
        _git(checkout, "cat-file", "-e", f"{commit}^{{commit}}")
        return
    except subprocess.CalledProcessError:
        pass
    shallow = _git(checkout, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    try:
        _git(checkout, "fetch", "--quiet", *(["--depth", "1"] if shallow else []), "origin", commit)
        _git(checkout, "cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError as e:
        raise DeployError(f"{checkout}: cannot fetch the pinned commit {commit[:9]}: {e.stderr.strip()}") from e


def prepare(dist):
    """Turn a generic build into a Pages one: no 404.html (Pages then serves index.html with
    status 200 for deep links) and the _headers file. Checks the Pages limits."""
    dist = Path(dist)
    if not (dist / "index.html").is_file():
        raise DeployError(f"{dist}/index.html is missing; run `npm run build` first")
    (dist / "404.html").unlink(missing_ok=True)
    shutil.copyfile(HEADERS_FILE, dist / "_headers")
    files = [p for p in dist.rglob("*") if p.is_file()]
    if len(files) >= MAX_FILES:
        raise DeployError(f"{dist} has {len(files)} files; Pages takes fewer than {MAX_FILES}")
    too_big = [p for p in files if p.stat().st_size >= MAX_FILE_BYTES]
    if too_big:
        names = ", ".join(str(p.relative_to(dist)) for p in too_big[:5])
        raise DeployError(f"files at or over {MAX_FILE_BYTES} bytes, which Pages refuses: {names}")
    return len(files)


def check_release(folder, pin):
    manifest = Path(folder) / "manifest.json"
    if not manifest.is_file():
        raise DeployError(f"{manifest} is missing; --release takes a `release build` output folder")
    data_commit = json.loads(manifest.read_text()).get("data_commit", "")
    if data_commit != pin.commit:
        raise DeployError(
            f"{folder} was built from {data_commit[:9] or 'an unknown commit'}, the pin is {pin.commit[:9]}; "
            "build it from the pin or move the pin in deploy/data-pin"
        )


def branch_for(args):
    if args.production:
        if args.branch not in (None, PRODUCTION_BRANCH):
            raise DeployError(f"--production deploys {PRODUCTION_BRANCH}; drop --branch {args.branch}")
        return PRODUCTION_BRANCH
    branch = args.branch or PREVIEW_BRANCH
    if branch == PRODUCTION_BRANCH:
        raise DeployError(f"{PRODUCTION_BRANCH} is production on Pages; pass --production to deploy it")
    return branch


def plan(args, work):
    """The commands for one deploy, in order. Nothing runs here."""
    pin = read_pin()
    branch = branch_for(args)
    work = Path(work)
    data_dir = work / "data"
    python = sys.executable
    steps = []

    if args.release:
        sync_source = ["--from-dir", str(args.release)]
    elif args.parlamento_aberto:
        checkout = work / "parlamento-aberto"
        release = work / "release"
        today = datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d")
        steps += [
            Step(
                "check out the pin",
                ["git", "-C", str(args.parlamento_aberto), "worktree", "add", "--detach", str(checkout), pin.commit],
            ),
            Step(
                "build the release",
                ["uv", "run", "--locked", "python", "-m", "parlamento_aberto.release", "build"]
                + ["--data", "data", "--out", str(release), "--sha", pin.commit, "--date", today],
                cwd=checkout,
            ),
        ]
        sync_source = ["--from-dir", str(release)]
    elif pin.tag:
        sync_source = ["--tag", pin.tag]
    else:
        raise DeployError("the pin has no release tag; pass --parlamento-aberto PATH or --release DIR")

    wrangler = shlex.split(os.environ.get("WRANGLER", DEFAULT_WRANGLER))
    steps += [
        Step("sync", [python, "-m", "fiscaliza_data", "sync", *sync_source, "--data-dir", str(data_dir)]),
        Step(
            "export",
            [
                python,
                "-m",
                "fiscaliza_data.export",
                "--out",
                str(FRONTEND / "public" / "api"),
                "--data-dir",
                str(data_dir),
            ],
        ),
        Step("install", ["npm", "ci"], cwd=FRONTEND),
        Step("build", ["npm", "run", "build"], cwd=FRONTEND),
        Step("prepare for Pages", ["prepare", str(FRONTEND / "dist")]),
        Step(
            "upload",
            [*wrangler, "pages", "deploy", "dist", "--project-name", PROJECT, "--branch", branch],
            cwd=FRONTEND,
        ),
    ]
    return steps


def run(args):
    pin = read_pin()
    branch_for(args)
    if args.release:
        check_release(args.release, pin)
    if args.dry_run:
        for step in plan(args, Path(args.work or "$WORK")):
            print(f"[{step.name}] (cd {step.cwd} && {shlex.join(step.argv)})")
        return 0
    if args.parlamento_aberto:
        fetch_pin(args.parlamento_aberto, pin.commit)
    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="fiscaliza-deploy-"))
    try:
        steps = plan(args, work)
        print(f"deploying parlamento-aberto {pin.commit[:9]} to Pages project {PROJECT}, branch {branch_for(args)}")
        for step in steps:
            print(f"[{step.name}]", flush=True)
            if step.argv[0] == "prepare":
                print(f"  {prepare(step.argv[1])} files")
                continue
            subprocess.run(step.argv, cwd=step.cwd, env={**os.environ, **step.env}, check=True)
    except subprocess.CalledProcessError as e:
        raise DeployError(f"{step.name} failed with exit code {e.returncode}") from e
    finally:
        if args.parlamento_aberto and (work / "parlamento-aberto").exists():
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(args.parlamento_aberto),
                    "worktree",
                    "remove",
                    "--force",
                    str(work / "parlamento-aberto"),
                ],
                check=False,
            )
        if not args.work and not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="deploy/pages.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deploy", help="build and upload to Pages")
    source = d.add_mutually_exclusive_group()
    source.add_argument("--parlamento-aberto", metavar="PATH", help="a parlamento-aberto clone to build the pin in")
    source.add_argument("--release", metavar="DIR", help="a `release build` output folder built from the pin")
    d.add_argument("--branch", help=f"Pages branch to deploy (default {PREVIEW_BRANCH})")
    d.add_argument("--production", action="store_true", help=f"deploy production ({PRODUCTION_BRANCH})")
    d.add_argument("--work", help="scratch folder (default: a temporary one, removed afterwards)")
    d.add_argument("--keep", action="store_true", help="keep the temporary scratch folder")
    d.add_argument("--dry-run", action="store_true", help="print the steps and run nothing")
    p = sub.add_parser("prepare", help="the Pages step alone, on a built dist/")
    p.add_argument("dist")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.cmd == "prepare":
            print(f"{prepare(args.dist)} files ready in {args.dist}")
            return 0
        return run(args)
    except DeployError as e:
        print(f"deploy failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
