"""IndexNow (deploy/pages.py): the key file, which URLs a production deploy submits, and a ping
that never fails the deploy."""

import importlib.util
import json
import re
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
S = "https://fiscaliza.pt"

spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

TEMPLATE = (FRONTEND / "index.html").read_text(encoding="utf-8")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def build(root, deputy_name="José Luís Carneiro", activity=1, party_deputies=2, asset="index-abc123.js"):
    """A prepared dist/ with one deputy, one party and one legislature of questions."""
    dist = root / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text(TEMPLATE.replace("</head>", f'<script src="/assets/{asset}"></script></head>'))
    api = dist / "api"
    write(api / "deputados.json", {"deputados": [{"id_cadastro": 2105, "nome": deputy_name, "partido_sigla": "PS"}]})
    write(api / "deputados" / "2105.json", {"atividades": activity})
    write(api / "partidos.json", {"partidos": [{"id": "PS", "sigla": "PS", "nome": "Partido Socialista"}]})
    write(api / "partidos" / "ps" / "deputados.json", {"total": party_deputies})
    write(api / "perguntas.json", {"legislaturas": [{"legislatura": "XVII"}]})
    write(api / "perguntas" / "xvii.json", {"perguntas": []})
    pages.prepare(dist)
    return dist, json.loads((dist / pages.INDEXNOW_MANIFEST).read_text())


def test_the_key_file_is_at_the_site_root_with_the_key_as_its_body():
    assert re.fullmatch(r"[0-9a-f]{32}", pages.INDEXNOW_KEY)
    assert (FRONTEND / "public" / f"{pages.INDEXNOW_KEY}.txt").read_text().strip() == pages.INDEXNOW_KEY


def test_the_manifest_has_every_sitemap_url(tmp_path):
    dist, manifest = build(tmp_path)
    locs = re.findall(r"<loc>([^<]+)</loc>", (dist / "sitemap.xml").read_text())
    assert manifest["version"] == 1
    assert sorted(manifest["pages"]) == sorted(locs)


def test_a_build_with_nothing_new_submits_nothing(tmp_path):
    _, before = build(tmp_path / "a")
    _, after = build(tmp_path / "b", asset="index-def456.js")
    assert pages.indexnow_changed(before, after) == []


def test_a_data_change_submits_only_that_page(tmp_path):
    _, before = build(tmp_path / "a")
    _, deputy = build(tmp_path / "b", activity=2)
    assert pages.indexnow_changed(before, deputy) == [f"{S}/deputados/2105"]
    _, party = build(tmp_path / "c", party_deputies=3)
    assert pages.indexnow_changed(before, party) == [f"{S}/partidos/PS"]


def test_a_new_head_submits_that_page(tmp_path):
    _, before = build(tmp_path / "a")
    _, after = build(tmp_path / "b", deputy_name="José Carneiro")
    assert pages.indexnow_changed(before, after) == [f"{S}/deputados/2105"]


def test_new_and_removed_urls_are_submitted():
    before = {"version": 1, "pages": {f"{S}/": "a", f"{S}/deputados/1": "b"}}
    after = {"version": 1, "pages": {f"{S}/": "a", f"{S}/deputados/2": "c"}}
    assert pages.indexnow_changed(before, after) == [f"{S}/deputados/2", f"{S}/deputados/1"]


def test_with_no_previous_manifest_every_url_is_submitted_once():
    after = {"version": 1, "pages": {f"{S}/": "a", f"{S}/deputados": "b"}}
    assert pages.indexnow_changed(None, after) == [f"{S}/", f"{S}/deputados"]
    assert pages.indexnow_changed({"not": "a manifest"}, after) == [f"{S}/", f"{S}/deputados"]


def test_the_payload_names_the_host_key_and_key_location():
    assert pages.indexnow_payload([f"{S}/"]) == {
        "host": "fiscaliza.pt",
        "key": pages.INDEXNOW_KEY,
        "keyLocation": f"{S}/{pages.INDEXNOW_KEY}.txt",
        "urlList": [f"{S}/"],
    }


def test_pinging_posts_once_skips_an_empty_list_and_never_raises():
    calls = []

    def ok(url, body):
        calls.append((url, json.loads(body)))
        return 202

    assert pages.indexnow_ping([], post=ok) == "IndexNow: nothing to submit"
    assert calls == []
    assert pages.indexnow_ping([f"{S}/"], post=ok) == "IndexNow answered 202 for 1 URL"
    assert calls == [("https://api.indexnow.org/indexnow", pages.indexnow_payload([f"{S}/"]))]

    def down(url, body):
        raise urllib.error.URLError("offline")

    assert pages.indexnow_ping([f"{S}/"], post=down).startswith("warning: IndexNow ping failed")


def test_a_live_manifest_that_cannot_be_read_skips_the_ping(tmp_path):
    _, after = build(tmp_path)

    def missing(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    def down(url):
        raise urllib.error.URLError("offline")

    assert pages.indexnow_urls(missing, after) == list(after["pages"])
    assert pages.indexnow_urls(down, after) is None
    assert pages.indexnow_urls(lambda url: b"not json", after) is None
    assert pages.indexnow_urls(lambda url: json.dumps(after).encode(), after) == []


def plan_names(argv):
    return [step.name for step in pages.plan(pages.parse_args(argv), work=Path("/work"))]


def test_only_production_pings_and_only_after_the_upload():
    production = plan_names(["deploy", "--release", "/rel", "--production"])
    assert production.index("read the live IndexNow manifest") < production.index("upload")
    assert production.index("upload") < production.index("ping IndexNow")
    preview = plan_names(["deploy", "--release", "/rel", "--branch", "x"])
    assert not [n for n in preview if "IndexNow" in n]
    assert not [n for n in plan_names(["build", "--release", "/rel"]) if "IndexNow" in n]


def test_a_failed_ping_does_not_fail_the_deploy(tmp_path, monkeypatch, capsys):
    dist, _ = build(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("anything")

    monkeypatch.setattr(pages, "indexnow_urls", boom)
    pages.run_indexnow_step("ping IndexNow", dist, tmp_path)
    assert "warning" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["PS", "MDP/CDE", "XVII", "PàF"])
def test_api_slugs_match_the_export(value):
    export = pytest.importorskip("fiscaliza_data.export")
    assert pages.api_slug(value) == export.slug(value)
