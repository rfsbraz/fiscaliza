"""Build Fiscaliza from the pinned parlamento-aberto commit and upload it to Cloudflare Pages.

    python deploy/pages.py deploy --parlamento-aberto PATH   # build the release from the pin
    python deploy/pages.py deploy --release DIR              # a release folder built from the pin
    python deploy/pages.py deploy ... --branch NAME          # preview branch (default: preview)
    python deploy/pages.py deploy ... --production           # production (master)
    python deploy/pages.py deploy ... --dry-run              # print the steps, run nothing
    python deploy/pages.py prepare DIST                      # only the Pages step on a built dist/
    python deploy/pages.py build --parlamento-aberto PATH    # local data from the pin, no upload

See docs/DEPLOY.md.
"""

import argparse
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
FRONTEND = ROOT / "frontend"
PIN_FILE = DEPLOY / "data-pin"
HEADERS_FILE = DEPLOY / "_headers"
REDIRECTS_FILE = DEPLOY / "_redirects"

PROJECT = "fiscaliza"
PRODUCTION_BRANCH = "master"
PREVIEW_BRANCH = "preview"
# Cloudflare Pages limits per deployment (free plan).
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024
SITE = "https://fiscaliza.pt"
SUFFIX = " · Fiscaliza"
# The head tags each route page sets, as (before the value)(value)(after). Each must be in
# frontend/index.html once; the rest of the page stays the app.
HEAD_TAGS = {
    "title": r"(<title>)([^<]*)(</title>)",
    "description": r'(<meta name="description" content=")([^"]*)("\s*/?>)',
    "canonical": r'(<link rel="canonical" href=")([^"]*)("\s*/?>)',
    "og:title": r'(<meta property="og:title" content=")([^"]*)("\s*/?>)',
    "og:description": r'(<meta property="og:description" content=")([^"]*)("\s*/?>)',
    "og:url": r'(<meta property="og:url" content=")([^"]*)("\s*/?>)',
}
# The app's routes with no id (frontend/src/App.jsx): title and description.
STATIC_ROUTES = {
    "/deputados": (
        "Deputados",
        "Os deputados da Assembleia da República desde 1975: mandatos, votações, presenças, "
        "intervenções e registo de interesses.",
    ),
    "/partidos": (
        "Partidos e coligações",
        "Os partidos e as coligações com deputados na Assembleia da República, com os seus deputados e votações.",
    ),
    "/agenda": ("Agenda", "As votações mais recentes e a atividade da Assembleia da República."),
    "/perguntas": (
        "Perguntas ao Governo",
        "As perguntas escritas dos deputados ao Governo, com as respostas e o tempo de resposta por legislatura.",
    ),
    "/metodologia": (
        "Metodologia e fontes",
        "Como o Fiscaliza trata os dados abertos da Assembleia da República: fontes, regras e limitações.",
    ),
}
# One path segment of a route that becomes a file name: no separators, no . or .., no controls.
SAFE_SEGMENT = re.compile(r"^(?!\.{1,2}$)[^/\\\x00-\x1f\x7f]+$")
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


def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _items(data, key):
    items = data.get(key) if isinstance(data, dict) else None
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def _route(prefix, value):
    """prefix/value when every segment of value is safe as a file name, else None."""
    value = str(value) if value is not None else ""
    segments = value.split("/")
    if not value or not all(SAFE_SEGMENT.match(s) for s in segments):
        return None
    return f"{prefix}/{value}"


def coalition_scope(region, years):
    """Which list and elections a coalition page is, as the page shows it (coalitionScope in
    frontend/src/utils/format.js): "Açores, 2025", "2024 e 2025", "1987 a 2025"."""
    years = [str(y) for y in years or [] if y is not None]
    if len(years) > 2:
        years = [f"{years[0]} a {years[-1]}"]
    return ", ".join(x for x in (region, " e ".join(years)) if x)


def route_heads(api):
    """{route path: (title, description)} for every app route the export has data for, plus the
    routes with no id. Reads the export's index files only; a missing one adds no routes."""
    api = Path(api)
    routes = dict(STATIC_ROUTES)

    for d in _items(_json(api / "deputados.json"), "deputados"):
        cad = d.get("id_cadastro")
        path = _route("/deputados", cad) if isinstance(cad, int) or str(cad).isdigit() else None
        name = (d.get("nome") or "").strip()
        if not path or not name:
            continue
        party, circle = d.get("partido_sigla"), d.get("circulo")
        context = ", ".join(x for x in (party, circle) if x)
        title = f"{name} ({party})" if party else name
        routes[path] = (
            title,
            f"Atividade parlamentar de {name}{f' ({context})' if context else ''}: votações, presenças, "
            "intervenções e registo de interesses na Assembleia da República.",
        )

    parties = {p.get("sigla") or p.get("id"): p.get("nome") for p in _items(_json(api / "partidos.json"), "partidos")}
    for f in sorted((api / "partidos").glob("*/deputados.json")) if (api / "partidos").is_dir() else []:
        party = (_json(f) or {}).get("partido")
        if isinstance(party, dict) and party.get("sigla"):
            parties.setdefault(party["sigla"], party.get("nome"))
    for sigla, name in parties.items():
        path = _route("/partidos", sigla)
        if path:
            label = f"{name} ({sigla})" if name and name != sigla else sigla
            routes[path] = (label, f"Deputados, votações e coligações: {label} na Assembleia da República.")

    for c in _items(_json(api / "coligacoes-todas.json"), "coligacoes"):
        path = _route("/coligacoes", c.get("id"))
        if path:
            name = c.get("nome") or c.get("sigla") or c["id"]
            scope = coalition_scope(c.get("ambito"), c.get("eleicoes"))
            label = f"{name} ({scope})" if scope else name
            routes[path] = (label, f"Partidos, deputados e eleições da coligação {label} na Assembleia da República.")

    for leg in _items(_json(api / "perguntas.json"), "legislaturas"):
        path = _route("/perguntas", leg.get("legislatura"))
        if path:
            n = leg["legislatura"]
            routes[path] = (
                f"Perguntas ao Governo na {n} legislatura",
                f"As perguntas escritas dos deputados ao Governo na {n} legislatura, com as respostas e o "
                "tempo de resposta.",
            )
    return routes


def render_head(template, path, title, description):
    """The app's index.html with this route's title, description, canonical and og:url."""
    url = SITE + quote(path, safe="/")
    values = {
        "title": title + SUFFIX,
        "description": description,
        "canonical": url,
        "og:title": title + SUFFIX,
        "og:description": description,
        "og:url": url,
    }
    out = template
    for key, pattern in HEAD_TAGS.items():
        value = html.escape(values[key], quote=True)
        out, n = re.subn(pattern, lambda m, v=value: m.group(1) + v + m.group(3), out, count=1)
        if n != 1:
            raise DeployError(f"index.html has no {key} tag to set for {path}")
    return out


def write_route_pages(dist):
    """One HTML file per app route, where Pages serves it: /deputados/2105 is deputados/2105.html.
    Link previews read these heads; the browser loads the same app. Returns the number written."""
    dist = Path(dist)
    template = (dist / "index.html").read_text(encoding="utf-8")
    if "<head" not in template:
        return 0
    written = 0
    for path, (title, description) in route_heads(dist / "api").items():
        target = dist / f"{path.lstrip('/')}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_head(template, path, title, description), encoding="utf-8")
        written += 1
    return written


def prepare(dist):
    """Turn a generic build into a Pages one: the _headers and _redirects files, a 404.html that
    is the app, and one HTML file per app route with its own head (write_route_pages). A route's
    file answers it with status 200; any other path with no file gets 404.html with status 404
    (#113). Checks the Pages limits."""
    dist = Path(dist)
    if not (dist / "index.html").is_file():
        raise DeployError(f"{dist}/index.html is missing; run `npm run build` first")
    if not (dist / "404.html").is_file():
        shutil.copyfile(dist / "index.html", dist / "404.html")
    shutil.copyfile(HEADERS_FILE, dist / "_headers")
    shutil.copyfile(REDIRECTS_FILE, dist / "_redirects")
    write_route_pages(dist)
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
    local = args.cmd == "build"
    branch = None if local else branch_for(args)
    work = Path(work)
    # A local build keeps its DuckDB file where the API and the dev tools look for it.
    data_dir = Path(args.data_dir) if local else work / "data"
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
    ]
    if local:
        return steps
    wrangler = shlex.split(os.environ.get("WRANGLER", DEFAULT_WRANGLER))
    steps += [
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
    local = args.cmd == "build"
    if not local:
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
        if local:
            print(f"building parlamento-aberto {pin.commit[:9]} into {args.data_dir} and frontend/public/api")
        else:
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
    b = sub.add_parser("build", help="build the pinned data locally: sync and export, no upload")
    source = b.add_mutually_exclusive_group(required=True)
    source.add_argument("--parlamento-aberto", metavar="PATH", help="a parlamento-aberto clone to build the pin in")
    source.add_argument("--release", metavar="DIR", help="a `release build` output folder built from the pin")
    b.add_argument("--data-dir", default="data", help="where the sync writes the DuckDB file (default: data)")
    b.add_argument("--work", help="scratch folder (default: a temporary one, removed afterwards)")
    b.add_argument("--keep", action="store_true", help="keep the temporary scratch folder")
    b.add_argument("--dry-run", action="store_true", help="print the steps and run nothing")
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
        print(f"{args.cmd} failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
