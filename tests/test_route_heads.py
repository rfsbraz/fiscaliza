"""Per-route heads (deploy/pages.py): one HTML file per app route with its own title, description,
canonical and og:url, so link previews (WhatsApp, X, Telegram) show the page and not the site.

Pages applies _redirects before it looks for a file, so a 200 rewrite of a route hides its file:
the routes have no rules and each one is a file. A path with no file still gets 404.html.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

TEMPLATE = (FRONTEND / "index.html").read_text(encoding="utf-8")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def dist(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(TEMPLATE, encoding="utf-8")
    api = dist / "api"
    deputy = {"id_cadastro": 2105, "nome": "José Luís Carneiro", "partido_sigla": "PS"}
    write(
        api / "deputados.json",
        {
            "deputados": [
                {**deputy, "circulo": "Braga", "legislatura_nome": "XVII"},
                {"id_cadastro": 99, "nome": 'Ana "A" <Silva> & Filhos', "partido_sigla": None, "circulo": None},
            ],
            "registos": [],
        },
    )
    write(api / "partidos.json", {"partidos": [{"id": "PS", "sigla": "PS", "nome": "Partido Socialista"}]})
    write(api / "partidos" / "ps" / "deputados.json", {"partido": {"sigla": "PS", "nome": "Partido Socialista"}})
    write(
        api / "partidos" / "mdp-cde" / "deputados.json",
        {"partido": {"sigla": "MDP/CDE", "nome": "Movimento Democrático Português"}},
    )
    write(
        api / "coligacoes-todas.json",
        {
            "coligacoes": [
                {
                    "id": "ad-2024",
                    "sigla": "AD",
                    "nome": "AD - Coligação PSD/CDS",
                    "ambito": None,
                    "eleicoes": [2024, 2025],
                },
                {"id": "ad-acores-2025", "sigla": "AD", "nome": "Aliança Democrática", "ambito": "Açores", "eleicoes": [2025]},
                {"id": "ad-1979", "sigla": "AD", "nome": "Aliança Democrática", "ambito": None, "eleicoes": [1979, 1980]},
                {"id": "PàF", "sigla": "PàF", "nome": "Portugal à Frente", "ambito": None, "eleicoes": [2015]},
            ]
        },
    )
    write(api / "perguntas.json", {"legislaturas": [{"legislatura": "XVII"}, {"legislatura": "XVI"}]})
    return dist


def head(html):
    """{tag key: value} for the tags each route sets."""
    out = {"title": re.search(r"<title>(.*?)</title>", html, re.S).group(1)}
    out["description"] = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
    out["canonical"] = re.search(r'<link rel="canonical" href="([^"]*)"', html).group(1)
    for prop in ("og:title", "og:description", "og:url"):
        out[prop] = re.search(rf'<meta property="{prop}" content="([^"]*)"', html).group(1)
    return out


def test_the_template_has_each_tag_once():
    for pattern in pages.HEAD_TAGS.values():
        assert len(re.findall(pattern, TEMPLATE)) == 1, pattern


def test_routes_cover_every_page_family(dist):
    routes = pages.route_heads(dist / "api")
    for path in (
        "/deputados",
        "/deputados/2105",
        "/deputados/99",
        "/partidos",
        "/partidos/PS",
        "/partidos/MDP/CDE",
        "/coligacoes/ad-2024",
        "/coligacoes/ad-acores-2025",
        "/coligacoes/PàF",
        "/agenda",
        "/perguntas",
        "/perguntas/XVII",
        "/perguntas/XVI",
        "/metodologia",
    ):
        assert path in routes, path
    assert "/" not in routes


def test_deputy_page_head(dist):
    pages.write_route_pages(dist)
    h = head((dist / "deputados" / "2105.html").read_text(encoding="utf-8"))
    assert h["title"] == "José Luís Carneiro (PS) · Fiscaliza"
    assert h["og:title"] == "José Luís Carneiro (PS) · Fiscaliza"
    assert "José Luís Carneiro" in h["description"] and "Braga" in h["description"]
    assert h["og:description"] == h["description"]
    assert h["canonical"] == h["og:url"] == "https://fiscaliza.pt/deputados/2105"


def test_text_is_escaped(dist):
    pages.write_route_pages(dist)
    html = (dist / "deputados" / "99.html").read_text(encoding="utf-8")
    assert "Ana &quot;A&quot; &lt;Silva&gt; &amp; Filhos" in head(html)["title"]
    assert "<Silva>" not in html


def test_files_sit_where_pages_serves_the_route(dist):
    pages.write_route_pages(dist)
    for rel in (
        "deputados.html",
        "deputados/2105.html",
        "partidos/PS.html",
        "partidos/MDP/CDE.html",
        "coligacoes/ad-2024.html",
        "coligacoes/ad-acores-2025.html",
        "coligacoes/PàF.html",
        "perguntas/XVII.html",
        "metodologia.html",
    ):
        assert (dist / rel).is_file(), rel


def test_canonical_urls_are_percent_encoded(dist):
    pages.write_route_pages(dist)
    h = head((dist / "coligacoes" / "PàF.html").read_text(encoding="utf-8"))
    assert h["canonical"] == "https://fiscaliza.pt/coligacoes/P%C3%A0F"


def test_coalition_pages_are_one_per_list_and_say_which(dist):
    # #111: the routes are the page ids, and two pages of one short name have different titles.
    routes = pages.route_heads(dist / "api")
    assert "/coligacoes/AD" not in routes
    assert routes["/coligacoes/ad-2024"][0] == "AD - Coligação PSD/CDS (2024 e 2025)"
    assert routes["/coligacoes/ad-acores-2025"][0] == "Aliança Democrática (Açores, 2025)"
    assert routes["/coligacoes/ad-1979"][0] == "Aliança Democrática (1979 e 1980)"
    assert routes["/coligacoes/PàF"][0] == "Portugal à Frente (2015)"
    assert pages.coalition_scope(None, [1987, 1991, 1995]) == "1987 a 1995"


def test_the_rest_of_the_page_is_the_app(dist):
    pages.write_route_pages(dist)
    html = (dist / "partidos" / "PS.html").read_text(encoding="utf-8")
    assert html.replace(head(html)["title"], "") != TEMPLATE
    assert '<div id="root"></div>' in html
    assert html.count("<title>") == 1
    # Everything outside the tags is the template.
    strip = lambda s: re.sub("|".join(pages.HEAD_TAGS.values()), "", s)  # noqa: E731
    assert strip(html) == strip(TEMPLATE)


def test_index_and_404_keep_the_site_head(dist):
    pages.prepare(dist)
    assert (dist / "index.html").read_text(encoding="utf-8") == TEMPLATE
    assert (dist / "404.html").read_text(encoding="utf-8") == TEMPLATE


def test_prepare_writes_the_route_pages_and_counts_them(dist):
    n = pages.prepare(dist)
    assert (dist / "deputados" / "2105.html").is_file()
    assert n == len([p for p in dist.rglob("*") if p.is_file()])


def test_a_build_without_the_export_still_prepares(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(TEMPLATE, encoding="utf-8")
    pages.prepare(dist)
    assert (dist / "deputados.html").is_file()
    assert not (dist / "deputados").exists()


def test_unsafe_ids_get_no_file(dist):
    write(
        dist / "api" / "deputados.json",
        {"deputados": [{"id_cadastro": "../../etc", "nome": "x"}, {"id_cadastro": 7, "nome": "Sete"}]},
    )
    pages.write_route_pages(dist)
    assert (dist / "deputados" / "7.html").is_file()
    assert not any(".." in str(p.relative_to(dist)) for p in dist.rglob("*"))


def redirect_rules():
    return [
        tuple(line.split())
        for line in pages.REDIRECTS_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_redirects_have_no_rule_for_a_route():
    # Pages applies a 200 rule before it looks for a file, so a rule would hide the route's page.
    # The only rules move the coalition pages that were split into one per list (#111).
    for source, destination, code in redirect_rules():
        assert code == "301", source
        assert source.startswith("/coligacoes/") and destination.startswith("/coligacoes/"), source
        assert "*" not in source and ":" not in source, source


def test_old_coalition_pages_move_to_the_latest_list():
    # /coligacoes/AD and /coligacoes/Madeira Primeiro were live and linked before the split.
    rules = {source: destination for source, destination, _ in redirect_rules()}
    for old in ("/coligacoes/AD", "/coligacoes/ad"):
        assert rules[old] == "/coligacoes/ad-2024", old
    for old in ("/coligacoes/Madeira%20Primeiro", "/coligacoes/madeira-primeiro"):
        assert rules[old] == "/coligacoes/madeira-primeiro-2024", old


def test_every_app_route_has_a_page(dist):
    app = (FRONTEND / "src" / "App.jsx").read_text()
    routes = pages.route_heads(dist / "api")
    for route in re.findall(r'<Route path="(/[^"]*)"', app):
        if route in ("/", "/*"):
            continue
        prefix = route.split("/:")[0]
        assert any(r == prefix or r.startswith(prefix + "/") for r in routes), route
