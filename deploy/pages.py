"""Build Fiscaliza from the pinned parlamento-aberto commit and upload it to Cloudflare Pages.

    python deploy/pages.py deploy --parlamento-aberto PATH   # build the release from the pin
    python deploy/pages.py deploy --release DIR              # a release folder built from the pin
    python deploy/pages.py deploy ... --branch NAME          # preview branch (default: preview)
    python deploy/pages.py deploy ... --production           # production (master)
    python deploy/pages.py deploy ... --dry-run              # print the steps, run nothing
    python deploy/pages.py prepare DIST                      # only the Pages step on a built dist/
    python deploy/pages.py build --parlamento-aberto PATH    # local data from the pin, no upload
    python deploy/pages.py build                             # local data from the pin's release tag

With tag= in the pin, the data comes from that published release on GitHub and
--parlamento-aberto is not used (the deploy workflow always passes it).

See docs/DEPLOY.md.
"""

import argparse
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request
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
# sitemaps.org limits per sitemap file; more URLs go into numbered files under a sitemap index.
SITEMAP_MAX_URLS = 50_000
SITEMAP_MAX_BYTES = 50 * 1024 * 1024
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
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
    "/privacidade": (
        "Privacidade",
        "O Fiscaliza não usa cookies nem pede dados pessoais: o que é contado e a quem é enviado.",
    ),
    "/dados": (
        "Descarregar dados",
        "Os dados abertos do Fiscaliza para descarregar: a release do parlamento-aberto em Parquet e CSV, "
        "com o manifest.json e a licença.",
    ),
}
# One path segment of a route that becomes a file name: no separators, no . or .., no controls.
SAFE_SEGMENT = re.compile(r"^(?!\.{1,2}$)[^/\\\x00-\x1f\x7f]+$")
# Wrangler 4 needs Node 22 or newer.
DEFAULT_WRANGLER = "npx --yes wrangler@4.151.3"
# IndexNow (#236). The key is public by design: engines check it against /<key>.txt, which is
# frontend/public/<key>.txt. Each deploy publishes INDEXNOW_MANIFEST, a hash per sitemap URL, and
# a production deploy submits the URLs whose hash differs from the live one.
INDEXNOW_KEY = "4400aea6a0cd479e278f0c5ef42087d7"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_MANIFEST = "indexnow-manifest.json"
# IndexNow takes at most 10 000 URLs per request.
INDEXNOW_MAX_URLS = 10_000


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


def route_url(path):
    """The canonical URL of a route, percent-encoded."""
    return SITE + quote(path, safe="/")


def render_head(template, path, title, description):
    """The app's index.html with this route's title, description, canonical and og:url."""
    url = route_url(path)
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


def write_route_pages(dist, routes=None):
    """One HTML file per app route, where Pages serves it: /deputados/2105 is deputados/2105.html.
    Link previews read these heads; the browser loads the same app. Returns the number written."""
    dist = Path(dist)
    template = (dist / "index.html").read_text(encoding="utf-8")
    if "<head" not in template:
        return 0
    written = 0
    for path, (title, description) in (route_heads(dist / "api") if routes is None else routes).items():
        target = dist / f"{path.lstrip('/')}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_head(template, path, title, description), encoding="utf-8")
        written += 1
    return written


def _sitemap_file(dist, name, root, tag, urls):
    body = "".join(f"<{tag}><loc>{html.escape(url)}</loc></{tag}>\n" for url in urls)
    data = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root} xmlns="{SITEMAP_NS}">\n{body}</{root}>\n'.encode()
    if len(data) > SITEMAP_MAX_BYTES:
        raise DeployError(f"{name} has {len(data)} bytes; a sitemap takes at most {SITEMAP_MAX_BYTES}")
    (Path(dist) / name).write_bytes(data)


def write_sitemap(dist, routes):
    """sitemap.xml with / and every route that has a page. Over SITEMAP_MAX_URLS it is an index of
    sitemap-1.xml, sitemap-2.xml, ... Returns the number of URLs."""
    urls = [route_url("/")] + [route_url(path) for path in routes]
    if len(urls) <= SITEMAP_MAX_URLS:
        _sitemap_file(dist, "sitemap.xml", "urlset", "url", urls)
        return len(urls)
    parts = []
    for i in range(0, len(urls), SITEMAP_MAX_URLS):
        name = f"sitemap-{len(parts) + 1}.xml"
        _sitemap_file(dist, name, "urlset", "url", urls[i : i + SITEMAP_MAX_URLS])
        parts.append(route_url("/" + name))
    _sitemap_file(dist, "sitemap.xml", "sitemapindex", "sitemap", parts)
    return len(urls)


def api_slug(value):
    """The export's path form of a party, coalition or legislature (fiscaliza_data.export.slug), or None."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or None


def page_hash(dist, path):
    """What a search engine would see change on a route: its HTML without scripts and links (their
    names follow each build), plus the export files under api/<kind>/<id> that the page reads."""
    dist = Path(dist)
    page = dist / ("index.html" if path == "/" else f"{path.lstrip('/')}.html")
    text = page.read_text(encoding="utf-8") if page.is_file() else ""
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<link\b[^>]*>", "", text)
    digest = hashlib.sha256(text.encode())
    kind, _, value = path.strip("/").partition("/")
    if value:
        api = dist / "api" / kind
        for name in sorted({value, api_slug(value)} - {None}):
            files = [api / f"{name}.json"]
            if (api / name).is_dir():
                files += sorted((api / name).rglob("*"))
            for f in files:
                if f.is_file():
                    digest.update(str(f.relative_to(dist)).encode() + b"\0" + f.read_bytes())
    return digest.hexdigest()[:16]


def indexnow_manifest(dist, routes):
    """{"version": 1, "pages": {sitemap URL: page_hash}} for / and every route."""
    return {"version": 1, "pages": {route_url(path): page_hash(dist, path) for path in ["/", *routes]}}


def indexnow_changed(previous, current):
    """New and changed URLs in sitemap order, then removed ones. With no previous manifest, every URL."""
    now = current["pages"]
    before = previous.get("pages") if isinstance(previous, dict) and previous.get("version") == 1 else None
    if not isinstance(before, dict):
        return list(now)
    return [url for url in now if before.get(url) != now[url]] + [url for url in before if url not in now]


def indexnow_payload(urls):
    return {
        "host": SITE.split("://", 1)[1],
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt",
        "urlList": list(urls),
    }


def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fiscaliza-deploy", "Cache-Control": "no-cache"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=30) as res:  # noqa: S310
        return res.read()


def _http_post(url, body):
    req = urllib.request.Request(  # noqa: S310
        url, data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:  # noqa: S310
            return res.status
    except urllib.error.HTTPError as e:
        return e.code


def indexnow_urls(get, current):
    """The URLs to submit against the live manifest. The first deploy (404) submits every URL; a live
    manifest that cannot be read gives None, and the ping is skipped rather than send everything."""
    try:
        previous = json.loads(get(f"{SITE}/{INDEXNOW_MANIFEST}"))
    except urllib.error.HTTPError as e:
        return indexnow_changed(None, current) if e.code == 404 else None
    except Exception:
        return None
    return indexnow_changed(previous, current)


def indexnow_ping(urls, post=_http_post):
    """POSTs the URLs to IndexNow and says what happened. Never raises."""
    if not urls:
        return "IndexNow: nothing to submit"
    try:
        status = post(INDEXNOW_ENDPOINT, json.dumps(indexnow_payload(urls[:INDEXNOW_MAX_URLS])).encode())
    except Exception as e:
        return f"warning: IndexNow ping failed: {e}"
    sent = len(urls[:INDEXNOW_MAX_URLS])
    return f"IndexNow answered {status} for {sent} URL{'' if sent == 1 else 's'}"


def run_indexnow_step(name, dist, work):
    """The two IndexNow steps of a production deploy. Any failure is a warning: the deploy goes on."""
    saved = Path(work) / "indexnow-urls.json"
    try:
        if name == "read the live IndexNow manifest":
            urls = indexnow_urls(_http_get, json.loads((Path(dist) / INDEXNOW_MANIFEST).read_text()))
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_text(json.dumps(urls))
            if urls is None:
                print("  warning: could not read the live IndexNow manifest; this deploy will not ping")
            else:
                print(f"  {len(urls)} URLs changed since the live deploy")
        else:
            urls = json.loads(saved.read_text())
            print("  warning: IndexNow skipped" if urls is None else f"  {indexnow_ping(urls)}")
    except Exception as e:
        print(f"  warning: {name} failed: {e}")


def prepare(dist):
    """Turn a generic build into a Pages one: the _headers and _redirects files, a 404.html that
    is the app, one HTML file per app route with its own head (write_route_pages) and a
    sitemap.xml of those routes (write_sitemap). A route's file answers it with status 200; any
    other path with no file gets 404.html with status 404 (#113). Checks the Pages limits."""
    dist = Path(dist)
    if not (dist / "index.html").is_file():
        raise DeployError(f"{dist}/index.html is missing; run `npm run build` first")
    if not (dist / "404.html").is_file():
        shutil.copyfile(dist / "index.html", dist / "404.html")
    shutil.copyfile(HEADERS_FILE, dist / "_headers")
    shutil.copyfile(REDIRECTS_FILE, dist / "_redirects")
    routes = route_heads(dist / "api")
    if write_route_pages(dist, routes):
        write_sitemap(dist, routes)
        (dist / INDEXNOW_MANIFEST).write_text(json.dumps(indexnow_manifest(dist, routes)), encoding="utf-8")
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


def builds_the_pin(args, pin):
    """Whether this run builds the release itself in a parlamento-aberto checkout: only when
    there is no --release folder and the pin has no published release tag."""
    return bool(args.parlamento_aberto) and not args.release and not pin.tag


def plan(args, work):
    """The commands for one deploy, in order. Nothing runs here.

    The data source, first match: --release DIR, the pin's release tag (synced from GitHub and
    checked against the pinned commit), a build of the pin in --parlamento-aberto PATH."""
    pin = read_pin(PIN_FILE)
    local = args.cmd == "build"
    branch = None if local else branch_for(args)
    work = Path(work)
    # A local build keeps its DuckDB file where the API and the dev tools look for it.
    data_dir = Path(args.data_dir) if local else work / "data"
    python = sys.executable
    steps = []

    if args.release:
        sync_source = ["--from-dir", str(args.release)]
    elif pin.tag:
        sync_source = ["--tag", pin.tag, "--data-commit", pin.commit]
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
    ]
    upload = Step(
        "upload",
        [*wrangler, "pages", "deploy", "dist", "--project-name", PROJECT, "--branch", branch],
        cwd=FRONTEND,
    )
    if branch != PRODUCTION_BRANCH:
        return [*steps, upload]
    # Only production tells IndexNow: read the live manifest before the upload replaces it, ping after.
    indexnow = ["indexnow", str(FRONTEND / "dist"), str(work)]
    return [*steps, Step("read the live IndexNow manifest", indexnow), upload, Step("ping IndexNow", indexnow)]


def run(args):
    pin = read_pin(PIN_FILE)
    local = args.cmd == "build"
    if not local:
        branch_for(args)
    if args.release:
        check_release(args.release, pin)
    if args.dry_run:
        for step in plan(args, Path(args.work or "$WORK")):
            print(f"[{step.name}] (cd {step.cwd} && {shlex.join(step.argv)})")
        return 0
    if builds_the_pin(args, pin):
        fetch_pin(args.parlamento_aberto, pin.commit)
    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="fiscaliza-deploy-"))
    try:
        steps = plan(args, work)
        source = f"release {pin.tag}" if pin.tag and not args.release else f"parlamento-aberto {pin.commit[:9]}"
        if local:
            print(f"building {source} into {args.data_dir} and frontend/public/api")
        else:
            print(f"deploying {source} to Pages project {PROJECT}, branch {branch_for(args)}")
        for step in steps:
            print(f"[{step.name}]", flush=True)
            if step.argv[0] == "prepare":
                print(f"  {prepare(step.argv[1])} files")
                continue
            if step.argv[0] == "indexnow":
                run_indexnow_step(step.name, step.argv[1], step.argv[2])
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
    # No source: the pin's release tag, from GitHub.
    source = b.add_mutually_exclusive_group()
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
