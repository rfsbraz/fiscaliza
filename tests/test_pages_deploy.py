"""Cloudflare Pages deploy: the pin, the Pages build output, the _headers file and the deploy plan."""

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)


# The pin


def test_pin_is_one_full_parlamento_aberto_commit():
    pin = pages.read_pin()
    assert re.fullmatch(r"[0-9a-f]{40}", pin.commit)
    assert pin.tag is None or re.fullmatch(r"data-\d{4}-\d{2}-\d{2}(\.\d+)?", pin.tag)


def test_pin_with_a_tag(tmp_path):
    f = tmp_path / "data-pin"
    f.write_text("# comment\ncommit=" + "a" * 40 + "\ntag=data-2026-10-21\n")
    pin = pages.read_pin(f)
    assert (pin.commit, pin.tag) == ("a" * 40, "data-2026-10-21")


def test_pin_rejects_a_short_commit(tmp_path):
    f = tmp_path / "data-pin"
    f.write_text("commit=31f894a\ntag=\n")
    with pytest.raises(pages.DeployError, match="40"):
        pages.read_pin(f)


def _git(*args, cwd):
    out = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _commit(repo, name):
    (repo / name).write_text(name)
    _git("add", name, cwd=repo)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", name, cwd=repo)
    return _git("rev-parse", "HEAD", cwd=repo)


@pytest.fixture
def upstream(tmp_path):
    repo = tmp_path / "upstream"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "uploadpack.allowReachableSHA1InWant", "true", cwd=repo)
    return repo


def _has(checkout, commit):
    r = subprocess.run(["git", "-C", str(checkout), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True)
    return r.returncode == 0


def test_fetch_pin_gets_the_exact_commit_a_clone_is_missing(tmp_path, upstream):
    pinned = _commit(upstream, "a")
    _git("clone", "-q", str(upstream), str(tmp_path / "old"), cwd=tmp_path)
    newer = _commit(upstream, "b")
    pages.fetch_pin(tmp_path / "old", newer)
    assert _has(tmp_path / "old", newer)
    assert _has(tmp_path / "old", pinned)


def test_fetch_pin_in_a_shallow_clone_of_a_main_that_moved_on(tmp_path, upstream):
    # CI clones main one commit deep; the pin can be behind it.
    pinned = _commit(upstream, "a")
    _commit(upstream, "b")
    _git("clone", "-q", "--depth", "1", "--no-checkout", f"file://{upstream}", str(tmp_path / "ci"), cwd=tmp_path)
    assert not _has(tmp_path / "ci", pinned)
    pages.fetch_pin(tmp_path / "ci", pinned)
    assert _has(tmp_path / "ci", pinned)


def test_fetch_pin_needs_a_git_clone(tmp_path):
    with pytest.raises(pages.DeployError, match="parlamento-aberto"):
        pages.fetch_pin(tmp_path, "a" * 40)


# The Pages build output


def _dist(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "api").mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    (dist / "404.html").write_text("<!doctype html><div id=root></div>")
    (dist / "assets" / "index-abc123.js").write_text("console.log(1)")
    (dist / "api" / "partidos.json").write_text("[]")
    return dist


def test_prepare_keeps_404_html_so_unknown_paths_answer_404(tmp_path):
    # #113: with a top-level 404.html Pages answers a path with no file and no rule with it and
    # status 404. The build's 404.html is the app, which shows its "page not found" view.
    dist = _dist(tmp_path)
    pages.prepare(dist)
    assert (dist / "404.html").read_text() == (dist / "index.html").read_text()
    assert (dist / "api" / "partidos.json").read_text() == "[]"
    assert (dist / "assets" / "index-abc123.js").exists()


def test_prepare_copies_the_redirects_file(tmp_path):
    dist = _dist(tmp_path)
    pages.prepare(dist)
    assert (dist / "_redirects").read_text() == pages.REDIRECTS_FILE.read_text()


def test_prepare_copies_the_headers_file(tmp_path):
    dist = _dist(tmp_path)
    pages.prepare(dist)
    assert (dist / "_headers").read_text() == pages.HEADERS_FILE.read_text()


def test_prepare_writes_404_html_when_the_build_has_none(tmp_path):
    dist = _dist(tmp_path)
    (dist / "404.html").unlink()
    pages.prepare(dist)
    assert (dist / "_headers").exists()
    assert (dist / "404.html").read_text() == (dist / "index.html").read_text()


# The _redirects file: the app's routes answer 200 with the app, everything else 404 (#113).


def redirect_rules():
    rules = []
    for line in pages.REDIRECTS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rules.append(tuple(line.split()))
    return rules


def app_routes():
    app = (FRONTEND / "src" / "App.jsx").read_text()
    return re.findall(r'<Route path="(/[^"]*)"', app)


def test_every_app_route_is_rewritten_to_the_app():
    rules = {source: (target, code) for source, target, code in redirect_rules()}
    for route in app_routes():
        if route in ("/", "/*"):
            continue
        source = re.sub(r"/:[^/]+$", "/*", route)
        # Pages turns /index.html into /, so a rewrite to it would loop; rewrite to / instead.
        assert rules.get(source) == ("/", "200"), route


def test_no_catch_all_and_no_api_rewrite():
    for source, _, _ in redirect_rules():
        assert source not in ("/*", "/"), source
        assert not source.startswith("/api"), source


def test_robots_txt_is_a_real_file_and_there_is_no_sitemap():
    public = FRONTEND / "public"
    robots = (public / "robots.txt").read_text()
    assert robots.startswith("User-agent: *")
    assert "<" not in robots
    # No sitemap.xml: Pages answers it with 404.html and status 404.
    assert not (public / "sitemap.xml").exists()
    assert "Sitemap:" not in robots


def test_app_has_a_not_found_route_that_is_not_indexed():
    app = (FRONTEND / "src" / "App.jsx").read_text()
    assert '<Route path="*" element={<NotFound />} />' in app
    view = (FRONTEND / "src" / "components" / "NotFound.jsx").read_text()
    assert "Página não encontrada" in view
    assert "noindex" in view
    assert 'to="/"' in view


def test_prepare_refuses_a_folder_without_index_html(tmp_path):
    dist = _dist(tmp_path)
    (dist / "index.html").unlink()
    with pytest.raises(pages.DeployError, match="index.html"):
        pages.prepare(dist)


def test_prepare_refuses_more_files_than_pages_allows(tmp_path, monkeypatch):
    dist = _dist(tmp_path)
    monkeypatch.setattr(pages, "MAX_FILES", 3)
    with pytest.raises(pages.DeployError, match="files"):
        pages.prepare(dist)


def test_prepare_refuses_a_file_over_the_pages_size_limit(tmp_path, monkeypatch):
    dist = _dist(tmp_path)
    monkeypatch.setattr(pages, "MAX_FILE_BYTES", 5)
    with pytest.raises(pages.DeployError, match="partidos.json|index"):
        pages.prepare(dist)


def test_default_build_still_writes_404_html_for_other_hosts():
    # The Pages mode is a step after the build; the plain `npm run build` stays generic.
    vite = (FRONTEND / "vite.config.js").read_text()
    assert "'404.html'" in vite
    assert "_headers" not in vite


# The _headers file


def parse_headers(text):
    """Cloudflare's _headers format: a path line, then indented `Name: value` lines."""
    rules, current = {}, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            current = rules.setdefault(line.strip(), {})
            continue
        name, _, value = line.strip().partition(":")
        assert current is not None, line
        assert name not in current, f"{name} twice under one path"
        current[name.strip().lower()] = value.strip()
    return rules


@pytest.fixture(scope="module")
def headers():
    return parse_headers(pages.HEADERS_FILE.read_text())


def csp(headers):
    policy = headers["/*"]["content-security-policy"]
    out = {}
    for directive in policy.split(";"):
        parts = directive.split()
        if parts:
            out[parts[0]] = parts[1:]
    return out


def test_hashed_assets_are_immutable_for_a_year(headers):
    cache = headers["/assets/*"]["cache-control"]
    assert "immutable" in cache
    assert "max-age=31536000" in cache


@pytest.mark.parametrize("path", ["/", "/index.html"])
def test_index_html_is_not_cached(headers, path):
    assert "no-cache" in headers[path]["cache-control"]


def test_api_has_a_short_ttl(headers):
    cache = headers["/api/*"]["cache-control"]
    age = int(re.search(r"max-age=(\d+)", cache).group(1))
    assert 0 < age <= 600


def test_catch_all_sets_no_cache_control(headers):
    # Pages joins a header from every matching rule with a comma, so a Cache-Control on /*
    # would land on the assets and the API next to their own.
    assert "cache-control" not in headers["/*"]


def test_security_headers(headers):
    h = headers["/*"]
    hsts = h["strict-transport-security"]
    assert int(re.search(r"max-age=(\d+)", hsts).group(1)) >= 31536000
    assert "preload" not in hsts
    assert h["x-content-type-options"] == "nosniff"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"


def test_csp_is_strict_where_it_can_be(headers):
    policy = csp(headers)
    assert policy["default-src"] == ["'self'"]
    assert policy["frame-ancestors"] == ["'none'"]
    assert policy["object-src"] == ["'none'"]
    assert "'unsafe-inline'" not in policy["script-src"]
    assert "'unsafe-eval'" not in policy["script-src"]
    assert policy["connect-src"] == ["'self'", "https://cloudflareinsights.com", *sentry_ingest()]


def test_csp_allows_what_the_app_loads(headers):
    policy = csp(headers)
    # The fonts are self-hosted (frontend/src/assets/fonts), so no font CDN is allowed.
    # Recharts and framer-motion set style attributes, hence 'unsafe-inline'.
    assert policy["style-src"] == ["'self'", "'unsafe-inline'"]
    assert policy["font-src"] == ["'self'"]

    sources = [FRONTEND / "index.html", *FRONTEND.glob("src/**/*.js*")]
    img_hosts = set()
    for f in sources:
        img_hosts |= set(re.findall(r"""src=\{?[`"']https://([^/`"'$]+)""", f.read_text()))
    stylesheet_hosts = set(
        re.findall(
            r'href="https://([^/"]+)/[^"]*"[^>]*rel="stylesheet"|rel="stylesheet"[^>]*href="https://([^/"]+)',
            (FRONTEND / "index.html").read_text(),
        )
    )
    assert img_hosts, "expected the deputy photos from parlamento.pt"
    for host in img_hosts:
        assert f"https://{host}" in policy["img-src"], host
    for pair in stylesheet_hosts:
        for host in filter(None, pair):
            assert f"https://{host}" in policy["style-src"], host


def test_csp_allows_cloudflare_web_analytics(headers):
    # Pages injects the Web Analytics beacon from static.cloudflareinsights.com,
    # and the beacon reports to cloudflareinsights.com.
    policy = csp(headers)
    assert policy["script-src"] == ["'self'", "https://static.cloudflareinsights.com"]
    assert policy["connect-src"] == ["'self'", "https://cloudflareinsights.com", *sentry_ingest()]


def test_csp_allows_the_deputy_photos_the_api_points_to(headers):
    # picture_url in the API answers, rendered by DeputadosPage, DeputadoDetalhes and PartidoDetalhes.
    core = (ROOT / "app" / "services" / "core.py").read_text()
    host = re.search(r'PICTURE_URL = "https://([^/"]+)/', core).group(1)
    assert f"https://{host}" in csp(headers)["img-src"]


# The deploy plan


def commands(argv):
    return [step.argv for step in pages.plan(pages.parse_args(argv), work=Path("/work"))]


def wrangler(argv):
    (cmd,) = [c for c in commands(argv) if "pages" in c and "deploy" in c]
    return cmd


def test_deploys_a_preview_by_default():
    cmd = wrangler(["deploy", "--release", "/rel"])
    assert cmd[cmd.index("--project-name") + 1] == "fiscaliza"
    assert cmd[cmd.index("--branch") + 1] == "preview"


def test_a_pull_request_deploys_its_own_branch():
    cmd = wrangler(["deploy", "--parlamento-aberto", "/pa", "--branch", "deploy/ci-workflow"])
    assert cmd[cmd.index("--branch") + 1] == "deploy/ci-workflow"


def test_production_needs_the_flag():
    with pytest.raises(pages.DeployError, match="--production"):
        commands(["deploy", "--parlamento-aberto", "/pa", "--branch", "master"])
    cmd = wrangler(["deploy", "--parlamento-aberto", "/pa", "--production"])
    assert cmd[cmd.index("--branch") + 1] == "master"


def test_production_flag_and_another_branch_conflict():
    with pytest.raises(pages.DeployError):
        commands(["deploy", "--parlamento-aberto", "/pa", "--production", "--branch", "x"])


def test_wrangler_is_pinned_to_one_version():
    assert re.fullmatch(r"npx --yes wrangler@4\.\d+\.\d+", pages.DEFAULT_WRANGLER)


def test_steps_run_in_order():
    cmds = [" ".join(c) for c in commands(["deploy", "--release", "/rel"])]
    order = ["fiscaliza_data sync", "fiscaliza_data.export", "npm ci", "npm run build", "pages deploy"]
    found = [next(i for i, c in enumerate(cmds) if key in c) for key in order]
    assert found == sorted(found)
    sync = next(c for c in cmds if "fiscaliza_data sync" in c)
    assert "--from-dir /rel" in sync
    export = next(c for c in cmds if "fiscaliza_data.export" in c)
    assert str(FRONTEND / "public" / "api") in export


def test_builds_the_pinned_commit_from_a_parlamento_aberto_checkout():
    pin = pages.read_pin()
    cmds = [" ".join(c) for c in commands(["deploy", "--parlamento-aberto", "/pa"])]
    assert any("worktree add --detach" in c and pin.commit in c for c in cmds)
    build = next(c for c in cmds if "parlamento_aberto.release build" in c)
    assert f"--sha {pin.commit}" in build
    sync = next(c for c in cmds if "fiscaliza_data sync" in c)
    assert "--from-dir /work/release" in sync


def test_a_release_folder_must_come_from_the_pin(tmp_path):
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / "manifest.json").write_text('{"tag": "data-2026-10-20", "data_commit": "' + "b" * 40 + '"}')
    with pytest.raises(pages.DeployError, match="pin"):
        pages.check_release(rel, pages.read_pin())


def test_build_makes_the_local_data_from_the_pin_without_uploading():
    pin = pages.read_pin()
    args = pages.parse_args(["build", "--parlamento-aberto", "/pa", "--data-dir", "/d"])
    cmds = [" ".join(step.argv) for step in pages.plan(args, work=Path("/work"))]
    assert any("worktree add --detach" in c and pin.commit in c for c in cmds)
    assert any("parlamento_aberto.release build" in c and f"--sha {pin.commit}" in c for c in cmds)
    sync = next(c for c in cmds if "fiscaliza_data sync" in c)
    assert "--from-dir /work/release" in sync and "--data-dir /d" in sync
    export = next(c for c in cmds if "fiscaliza_data.export" in c)
    assert f"--out {FRONTEND / 'public' / 'api'}" in export and "--data-dir /d" in export
    # Nothing past the export: no npm build, no Pages step, no upload.
    assert cmds[-1] == export
    assert not any("wrangler" in c or "pages deploy" in c or c.startswith("prepare") for c in cmds)


def test_build_defaults_the_data_dir_to_data():
    args = pages.parse_args(["build", "--parlamento-aberto", "/pa"])
    sync = next(" ".join(s.argv) for s in pages.plan(args, work=Path("/work")) if "fiscaliza_data" in s.argv)
    assert "--data-dir data" in sync


def test_build_takes_no_pages_branch():
    with pytest.raises(SystemExit):
        pages.parse_args(["build", "--parlamento-aberto", "/pa", "--branch", "x"])


# Sentry (errors only)

SENTRY_JS = FRONTEND / "src" / "sentry.js"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def sentry_dsn():
    m = re.search(r"^\s+VITE_SENTRY_DSN: '?([^'\s#]*)'?", DEPLOY_WORKFLOW.read_text(), re.M)
    return m.group(1) if m else ""


def test_sentry_reports_errors_only_without_personal_data():
    src = SENTRY_JS.read_text()
    assert "sendDefaultPii: false" in src
    for banned in (
        "browserTracingIntegration",
        "replayIntegration",
        "tracesSampleRate",
        "tracesSampler",
        "replaysSessionSampleRate",
        "replaysOnErrorSampleRate",
        "profilesSampleRate",
        "browserProfilingIntegration",
    ):
        assert banned not in src, banned
    # Only the app's entry point initialises it.
    main = (FRONTEND / "src" / "main.jsx").read_text()
    assert "initSentry()" in main
    assert "AppErrorBoundary" in main


def test_no_sentry_auth_files_are_committed():
    for name in (".env.sentry-build-plugin", ".sentryclirc"):
        assert not (FRONTEND / name).exists(), name
        assert not (ROOT / name).exists(), name


def sentry_ingest():
    """The ingest origin of the DSN in deploy.yml, as a list: empty while no DSN is set."""
    dsn = sentry_dsn()
    return [f"https://{re.match(r'https://[^@]+@([^/]+)/', dsn).group(1)}"] if dsn else []


def test_csp_allows_the_sentry_ingest_host(headers):
    if not sentry_dsn():
        pytest.skip("VITE_SENTRY_DSN is not set in deploy.yml yet")
    assert sentry_ingest()[0] in csp(headers)["connect-src"]
