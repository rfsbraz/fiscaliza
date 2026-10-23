"""The download page, /dados (#186): the live release's files, their sizes and licences.

The export writes api/dados.json from what the sync kept of the release: its manifest.json and
the real size of every file. A local build of the pin is not on GitHub, so its files have no
download URL; a release synced from GitHub links each asset.
"""

import gzip
import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

from app.services import core
from fiscaliza_data import export, sync
from tests.site_data import TAG, build_release, build_site_data

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)
RELEASE_URL = f"https://github.com/rfsbraz/parlamento-aberto/releases/tag/{TAG}"
DOWNLOAD = f"https://github.com/rfsbraz/parlamento-aberto/releases/download/{TAG}/"


class GitHubRelease:
    """Serves a release folder as the GitHub API and asset downloads would, sizes included."""

    def __init__(self, folder):
        self.folder = folder

    def get_json(self, url):
        assets = [
            {"name": p.name, "size": p.stat().st_size, "browser_download_url": DOWNLOAD + p.name}
            for p in sorted(self.folder.iterdir())
        ]
        return {"tag_name": TAG, "html_url": RELEASE_URL, "assets": assets}

    def download(self, url, dest):
        dest.write_bytes((self.folder / url.rsplit("/", 1)[1]).read_bytes())


def published_release(root):
    """The synthetic release as data-release.yml publishes it: a CSV next to each Parquet file,
    licences in the manifest, the changelog."""
    folder = build_release(Path(root) / "release")
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["licence"] = {"marts": "CC BY 4.0"}
    for name, mart in manifest["marts"].items():
        csv = folder / f"{name}.csv.gz"
        csv.write_bytes(gzip.compress(f"# {name}\n".encode()))
        mart["files"]["csv"] = {"name": csv.name, "sha256": "0" * 64}
    manifest["marts"]["deputies"]["licence"] = "Fora da licença dos marts"
    (folder / "manifest.json").write_text(json.dumps(manifest))
    (folder / "CHANGELOG.md").write_text("# Alterações\n")
    return folder


@pytest.fixture(scope="module")
def local_con(tmp_path_factory):
    data_dir = build_site_data(tmp_path_factory.mktemp("local"))
    con = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield con
    con.close()


@pytest.fixture(scope="module")
def published(tmp_path_factory):
    root = tmp_path_factory.mktemp("published")
    folder = published_release(root)
    data_dir = root / "data"
    sync.sync(data_dir, http=GitHubRelease(folder))
    return folder, data_dir


@pytest.fixture(scope="module")
def published_con(published):
    con = duckdb.connect(str(published[1] / "current.duckdb"), read_only=True)
    yield con
    con.close()


def test_a_local_build_lists_the_files_without_links(local_con):
    body = core.dados(local_con)
    assert body["tag"] == TAG and body["publicado"] is False and body["release_url"] is None
    assert body["source_updated"] == "2026-10-20" and body["schema_version"] == "1.2.0"
    sets = {s["nome"]: s for s in body["conjuntos"]}
    assert "deputies" in sets and "mandates" in sets
    deputies = sets["deputies"]
    assert deputies["parquet"]["nome"] == "deputies.parquet"
    assert deputies["parquet"]["bytes"] > 0 and deputies["parquet"]["url"] is None
    assert deputies["csv"] is None  # the synthetic release has no CSV
    assert body["manifest"]["nome"] == "manifest.json" and body["manifest"]["url"] is None
    assert body["total_parquet"] == sum(s["parquet"]["bytes"] for s in body["conjuntos"])
    assert core.health(local_con)["data"]["publicado"] is False


def test_a_published_release_links_every_file_with_its_real_size(published, published_con):
    folder, _ = published
    body = core.dados(published_con)
    assert body["publicado"] is True and body["release_url"] == RELEASE_URL
    sets = {s["nome"]: s for s in body["conjuntos"]}
    for name, s in sets.items():
        for kind, file_name in (("parquet", f"{name}.parquet"), ("csv", f"{name}.csv.gz")):
            assert s[kind] == {
                "nome": file_name,
                "bytes": (folder / file_name).stat().st_size,
                "url": DOWNLOAD + file_name,
            }
    assert body["manifest"]["url"] == DOWNLOAD + "manifest.json"
    assert body["changelog"]["url"] == DOWNLOAD + "CHANGELOG.md"
    assert body["total_csv"] == sum((folder / f"{n}.csv.gz").stat().st_size for n in sets)
    assert core.health(published_con)["data"]["publicado"] is True


def test_licences_come_from_the_manifest(published_con):
    sets = {s["nome"]: s for s in core.dados(published_con)["conjuntos"]}
    assert sets["mandates"]["licenca"] == "CC BY 4.0" and sets["mandates"]["cc_by"] is True
    assert sets["deputies"]["licenca"] == "Fora da licença dos marts" and sets["deputies"]["cc_by"] is False


def test_the_order_is_the_manifest_order(published, published_con):
    folder, _ = published
    manifest = json.loads((folder / "manifest.json").read_text())
    assert [s["nome"] for s in core.dados(published_con)["conjuntos"]] == list(manifest["marts"])


def test_a_file_synced_before_the_release_tables_has_no_files():
    con = duckdb.connect()
    con.execute(
        "create table _meta as select 'data-2026-10-01' as tag, '1.2.0' as schema_version, "
        "'2026-10-01' as source_updated, null as data_commit, now() as synced_at"
    )
    body = core.dados(con)
    assert body["tag"] == "data-2026-10-01" and body["publicado"] is False and body["conjuntos"] == []
    assert core.health(con)["data"]["publicado"] is False


def test_export_writes_dados_json(published, tmp_path):
    _, data_dir = published
    out = tmp_path / "api"
    export.export(data_dir, out, jobs=1)
    body = json.loads((out / "dados.json").read_text())
    assert body["publicado"] is True and body["manifest"]["url"] == DOWNLOAD + "manifest.json"


def test_api_route_serves_the_same_payload(app, published):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, published[1])
    try:
        response = app.test_client().get("/api/dados")
        assert response.status_code == 200
        assert response.get_json()["release_url"] == RELEASE_URL
    finally:
        app.extensions[connection.EXTENSION] = before


def test_static_client_serves_dados_json():
    assert "if (route === 'dados' && none) return serve('dados.json');" in (SRC / "config" / "staticApi.js").read_text()


def test_route_page_link_and_head():
    app = (SRC / "App.jsx").read_text()
    route = app.index('<Route path="/dados" element={<Dados />} />')
    assert route < app.index('<Route path="*" element={<NotFound />} />')
    assert 'to="/dados"' in (SRC / "components" / "FreshnessBar.jsx").read_text()
    # deploy/pages.py writes dados.html with its own head, and the sitemap lists it.
    assert pages.STATIC_ROUTES["/dados"][0] == "Descarregar dados"
    page = (SRC / "components" / "Dados.jsx").read_text()
    assert "Descarregar dados · Fiscaliza" in page and "apiFetch('dados')" in page
