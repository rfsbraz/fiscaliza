"""S4: the DuckDB repository, site views and the core pages it serves.

Values are checked against the synthetic release in tests/site_data.py: XVII has 230 seats
with the known split, a mid-term replacement and a substitute who never sat.
"""

import ast
import os
import re
from pathlib import Path

import duckdb
import pytest

from app.data.connection import DataSource, DataUnavailable
from app.services import core
from tests.site_data import EXTRACT, KNOWN_SPLIT, TAG, build_site_data

ROOT = Path(__file__).resolve().parent.parent
PORTED_ROUTES = {
    "/api/legislaturas",
    "/api/estatisticas",
    "/api/deputados",
    "/api/partidos",
    "/api/coligacoes",
    "/api/coligacoes/<path:coligacao_sigla>",
    "/api/coligacoes/<path:coligacao_sigla>/deputados",
    "/api/coligacoes/<path:coligacao_sigla>/partidos",
}


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


# Dashboard (F02)


def test_current_legislature_has_230_seats_with_the_known_split(con):
    stats = core.estatisticas(con)
    assert stats["legislatura"]["numero"] == "XVII"
    assert stats["legislatura"]["data_referencia"] == EXTRACT
    assert stats["totais"]["deputados"] == 230
    assert stats["totais"]["deputados_em_exercicio"] == 230
    assert stats["totais"]["seated_deputies"] == 230
    assert {p["sigla"]: p["deputados"] for p in stats["distribuicao_partidos"]} == KNOWN_SPLIT
    assert [p["sigla"] for p in stats["distribuicao_partidos"]][:3] == ["PSD", "CH", "PS"]
    assert stats["totais"]["partidos"] == 10


def test_elected_counts_everyone_who_held_a_seat_in_the_legislature(con):
    # 230 seated now, plus person 231 who resigned and person 303, seated for one day. Person
    # 500 is a substitute who never sat, and 302 and 501 were elected but never took the seat.
    assert core.estatisticas(con)["totais"]["deputados_eleitos"] == 232


def test_circle_distribution_is_the_top_ten_circles_by_seats(con):
    circles = core.estatisticas(con)["distribuicao_circulos"]
    assert len(circles) == 10
    seats = [c["deputados"] for c in circles]
    assert seats == sorted(seats, reverse=True)


def test_a_closed_legislature_is_read_on_its_last_day(con):
    stats = core.estatisticas(con, "XVI")
    assert stats["legislatura"]["data_referencia"] == "2025-06-02"
    assert stats["totais"]["deputados"] == 230
    assert stats["legislatura"]["ativa"] is False


def test_unknown_legislature_is_not_found(con):
    with pytest.raises(core.NotFound):
        core.estatisticas(con, "XL")


# Legislature selector (F01)


def test_legislatures_newest_first(con):
    legs = core.legislaturas(con)["legislaturas"]
    assert [(leg["numero"], leg["ativa"], leg["total_deputados"]) for leg in legs] == [
        ("XVII", True, 232),
        ("XVI", False, 230),
    ]
    assert legs[0]["data_inicio"] == "2025-06-03" and legs[0]["data_fim"] is None


def test_legislatures_carry_their_published_interventions(con):
    legs = core.legislaturas(con)["legislaturas"]
    assert [(leg["numero"], leg["intervencoes_publicadas"]) for leg in legs] == [("XVII", 11), ("XVI", 5)]


def test_legislatures_carry_the_declaration_coverage(con):
    # People with an effective mandate in the legislatures with AR declarations, each counted
    # once, and how many of them have one (#113). On the pin: 149 of 793 (XI to XV). The synthetic
    # release has AR declarations only for XVI among its legislatures, and only 301 has one.
    assert core.legislaturas(con)["cobertura_declaracoes"] == {
        "de": "XVI",
        "ate": "XVI",
        "com_declaracao": 1,
        "total": 230,
    }


def test_declaration_coverage_counts_people_with_an_effective_mandate_once():
    # Each person once, over the covered legislatures (793 with 149 declared on the pin), not
    # person-legislature pairs (1,425 and 297). Suplentes who never sat are not in the base.
    from app.data import repository

    c = duckdb.connect()
    c.execute("create table legislatures (legislature varchar, start_date date)")
    c.execute("insert into legislatures values ('XI', '2009-10-15'), ('XII', '2011-06-20'), ('XIII', '2015-10-23')")
    c.execute("create table mandates (legislature varchar, cadastro_id integer, is_effective boolean)")
    c.execute(
        "insert into mandates values ('XI', 1, true), ('XII', 1, true), ('XI', 2, true), ('XII', 3, true),"
        " ('XII', 4, false), ('XIII', 5, true)"
    )
    c.execute("create table interest_declarations (legislature varchar, cadastro_id integer, source varchar)")
    c.execute(
        "insert into interest_declarations values ('XI', 1, 'ar_open_data'), ('XII', 1, 'ar_open_data'),"
        " ('XII', 3, 'ar_open_data'), ('XII', 4, 'ar_open_data')"
    )
    coverage = repository.declaration_coverage(c)
    assert {k: coverage[k] for k in ("first_legislature", "last_legislature", "seated", "declared")} == {
        "first_legislature": "XI",
        "last_legislature": "XII",
        "seated": 3,
        "declared": 2,
    }


# Parties (F21)


def test_parties_have_their_seat_counts(con):
    parties = core.partidos(con)["partidos"]
    assert {p["sigla"]: p["num_deputados"] for p in parties} == KNOWN_SPLIT
    assert parties[0] == {
        "id": "PSD",
        "sigla": "PSD",
        "nome": "Grupo PSD",
        "num_deputados": 89,
        "percentagem": 38.7,
        "ativo": True,
    }


# Deputies list (F03)


def test_deputies_list_defaults_to_the_current_legislature_seated_first(con):
    page = core.deputados(con, per_page=100)
    # 234 elected or seated in XVII less 231, who resigned (#171).
    assert page["pagination"]["total"] == 233
    assert all(d["is_seated"] for d in page["deputados"])
    last = core.deputados(con, page=3, per_page=100)["deputados"]
    assert [(d["id_cadastro"], d["is_seated"], d["mandate_status"]) for d in last[-3:]] == [
        (302, False, "Suspenso(Eleito)"),
        (303, False, "Suspenso(Eleito)"),
        (501, False, "Suspenso(Eleito)"),
    ]


def test_a_resigned_deputy_is_found_through_the_legislature_filter(con):
    # 231 resigned on 2026-01-01: out of the default list, still in XVII when asked for it.
    default = core.deputados(con, page=3, per_page=100)["deputados"]
    assert 231 not in [d["id_cadastro"] for d in default]
    xvii = core.deputados(con, legislatura="XVII", per_page=100)
    assert xvii["pagination"]["total"] == 234
    found = {
        d["id_cadastro"]: d
        for p in (1, 2, 3)
        for d in core.deputados(con, legislatura="XVII", page=p, per_page=100)["deputados"]
    }
    assert (found[231]["legislatura_nome"], found[231]["mandate_status"]) == ("XVII", "Renunciou")


def test_a_resigned_deputy_is_in_the_current_legislature_but_not_in_office(con):
    # 231 is no longer in office in XVII. A suspended mandate (302) is still a mandate of the
    # current legislature.
    found = {d["id_cadastro"]: d for d in core.deputados(con, legislatura="XVII", page=3, per_page=100)["deputados"]}
    assert (found[231]["career_info"]["is_currently_active"], found[231]["career_info"]["in_current_legislature"]) == (
        False,
        True,
    )
    assert (found[302]["career_info"]["is_currently_active"], found[302]["career_info"]["in_current_legislature"]) == (
        True,
        True,
    )


def test_deputies_list_of_everyone_who_ever_sat(con):
    page = core.deputados(con, active_only=False)
    # 234 elected or seated in XVII plus 178 only in XVI; 500 is a substitute who never sat.
    assert page["pagination"]["total"] == 412
    assert page["filters"]["seated_deputies_count"] == 230
    assert page["filters"]["active_deputies_count"] == 232
    assert page["filters"]["total_deputy_records"] == 464  # 234 in XVII plus 230 in XVI


def test_deputy_career_across_legislatures(con):
    [d] = core.deputados(con, search="Deputado 1", active_only=False, per_page=100)["deputados"][:1]
    assert d["id_cadastro"] == 1
    assert d["partido_sigla"] == "PSD" and d["legislatura_nome"] == "XVII"
    career = d["career_info"]
    assert career["total_mandates"] == 2 and career["is_multi_term"] is True
    assert (career["first_mandate"], career["latest_mandate"]) == ("XVI", "XVII")
    assert career["parties_served"] == ["PS", "PSD"]
    assert career["is_currently_active"] is True and career["is_seated"] is True
    assert d["picture_url"].endswith("id=1&type=deputado")


def test_former_deputy_shows_the_latest_completed_mandate(con):
    [d] = core.deputados(con, search="deputado 300", active_only=False)["deputados"]
    assert d["career_info"]["is_currently_active"] is False
    assert d["career_info"]["latest_completed_mandate"] == {"legislatura": "XVI", "periodo": "2024-2025"}


def test_elected_people_who_never_sat_are_listed_and_found(con):
    # #107: elected with the mandate suspended from the start, never seated.
    [d] = core.deputados(con, search="deputado 501", active_only=False)["deputados"]
    assert (d["id_cadastro"], d["legislatura_nome"], d["is_seated"]) == (501, "XVII", False)
    assert d["mandate_status"] == "Suspenso(Eleito)" and d["partido_sigla"] is None
    assert d["career_info"]["total_mandates"] == 0 and d["career_info"]["is_currently_active"] is True
    assert d["circulo"] == "Círculo 18"


def test_a_suspended_xvii_mandate_is_the_latest_legislature(con):
    [d] = core.deputados(con, search="deputado 302", active_only=False)["deputados"]
    assert d["legislatura_nome"] == "XVII" and d["mandate_status"] == "Suspenso(Eleito)"
    career = d["career_info"]
    assert (career["first_mandate"], career["latest_mandate"]) == ("XVI", "XVII")
    # Seated legislatures only: the suspended one is not a mandate served.
    assert career["total_mandates"] == 1 and career["is_multi_term"] is False
    assert career["latest_completed_mandate"] == {"legislatura": "XVI", "periodo": "2024-2025"}


def test_search_ignores_case_and_accents(con):
    found = core.deputados(con, search="NOME COMPLÉTO 300", active_only=False)["deputados"]
    assert [d["id_cadastro"] for d in found] == [300]


def test_legislature_filter_and_paging(con):
    page = core.deputados(con, legislatura="XVI", page=2, per_page=500)
    assert page["pagination"]["per_page"] == 100
    assert page["pagination"]["total"] == 230
    assert len(page["deputados"]) == 100
    assert {d["legislatura_nome"] for d in page["deputados"]} == {"XVI"}


# Coalitions (F31)


def test_coalitions_active_by_default(con):
    assert [c["sigla"] for c in core.coligacoes(con)["coligacoes"]] == ["AD", "CDU"]
    every = {c["sigla"]: c for c in core.coligacoes(con, include_inactive=True)["coligacoes"]}
    assert sorted(every) == ["AD", "CDU", "FRS"]
    assert every["FRS"]["ativa"] is False and every["FRS"]["data_dissolucao"] == "2025-06-02"
    assert every["AD"]["ativa"] is True and every["AD"]["data_dissolucao"] is None
    assert every["AD"]["data_formacao"] == "2024-03-26"
    assert [p["sigla"] for p in every["AD"]["component_parties"]] == ["PSD", "CDS-PP", "PPM"]
    assert every["AD"]["deputy_count"] == AD_XVII_SCOPED


def test_coalition_dates_come_from_its_latest_unbroken_run():
    # AD ran in I-B and II, then again from XVI: today's AD starts with XVI.
    order = ["I-B", "II", "III", "XV", "XVI", "XVII"]
    assert core.latest_run(order, {"I-B", "II", "XVI", "XVII"}) == ["XVI", "XVII"]
    assert core.latest_run(order, {"I-B", "II"}) == ["I-B", "II"]


def test_coalition_detail_deputies_and_parties(con):
    assert core.coligacao(con, "AD")["nome"] == "Coligação AD"
    deputies = core.coligacao_deputados(con, "AD")["deputados"]
    assert len(deputies) == AD_XVII_SCOPED
    assert {d["partido_sigla"] for d in deputies} == {"PSD", "CDS-PP"}
    assert [p["sigla"] for p in core.coligacao_partidos(con, "AD")["partidos"]] == ["PSD", "CDS-PP", "PPM"]
    assert (
        len(core.coligacao_deputados(con, "FRS")["deputados"]) == 27
    )  # FRS ran in XVI only: PS there, person 1 included


# PSD and CDS-PP hold seats 1 to 91 in XVII (KNOWN_SPLIT), in circle cad % 22 + 1. AD's two lists
# won seats in circles 1 to 20 (ballot_list_seats), so the 8 of them in circles 21 and 22 are out.
AD_XVII_SCOPED = 83


def test_coalition_deputies_come_only_from_circles_where_its_lists_won_seats(con):
    # #181: every deputy of the coalition's groups was counted, whatever their circle.
    deputies = core.coligacao_deputados(con, "AD")["deputados"]
    circles = {d["circulo"] for d in deputies}
    assert "Círculo 21" not in circles and "Círculo 22" not in circles
    assert {f"Círculo {i}" for i in range(1, 21)} == circles  # circle 5's "a)" mark is ignored
    assert core.coligacao(con, "AD")["deputy_count"] == AD_XVII_SCOPED
    listed = {c["sigla"]: c for c in core.coligacoes(con)["coligacoes"]}
    assert listed["AD"]["deputy_count"] == AD_XVII_SCOPED
    ad_seats = con.execute(
        "select sum(seats) from ballot_list_seats where legislature = 'XVII' and ballot_acronym in ('AD-LISTA', 'AD-ACORES')"
    ).fetchone()[0]
    assert ad_seats == AD_XVII_SCOPED
    assert len(core.coligacao_deputados(con, "CDU")["deputados"]) == KNOWN_SPLIT["PCP"]


def test_coalition_deputies_keep_the_group_rule_without_seats_per_circle(con):
    # XVI has no ballot_list_seats rows, like every legislature before XI: all deputies of the
    # coalition's groups still count there.
    xvi = core.coligacao_deputados(con, "AD", "XVI")
    seated = con.execute(
        "select count(*) from seated_detail(date '2025-06-02') "
        "where legislature = 'XVI' and group_acronym in ('PSD', 'CDS-PP')"
    ).fetchone()[0]
    assert xvi["legislatura"] == "XVI" and xvi["total_deputados"] == seated > 0
    assert core.coligacao_deputados(con, "FRS")["total_deputados"] == 27


def test_coalition_parties_without_seats_are_marked(con):
    # #181: PPM ran on the Açores AD list and PEV on the CDU list without winning a seat.
    detail = core.coligacao(con, "AD")["component_parties"]
    assert [(p["sigla"], p["com_lugares"]) for p in detail] == [("PSD", True), ("CDS-PP", True), ("PPM", False)]
    parties = core.coligacao_partidos(con, "CDU")["partidos"]
    assert [(p["sigla"], p["com_lugares"]) for p in parties] == [("PCP", True), ("PEV", False)]
    for page in ("ColigacaoDetalhes.jsx", "PartidosPage.jsx"):
        assert "seatsNote(" in (ROOT / "frontend" / "src" / "components" / page).read_text(), page


def test_coalition_pages_show_no_unsourced_history_or_formation_date():
    # #111: the narratives and key moments were hard-coded, the "formation" date is the start
    # of a legislature, data_adesao likewise, and the results tab and spectrum badge are empty.
    page = (ROOT / "frontend" / "src" / "components" / "ColigacaoDetalhes.jsx").read_text()
    for text in (
        "Contexto Histórico",
        "Momentos Chave",
        "Sá Carneiro",
        "Alentejo",
        "geringonça",
        "maximizar a representação",
        ">Formação<",
        "Formação da Coligação",
        "data_formacao",
        "data_adesao",
        "Desempenho Eleitoral",
        "em desenvolvimento",
        "'N/A'",
    ):
        assert text not in page, text
    listing = (ROOT / "frontend" / "src" / "components" / "PartidosPage.jsx").read_text()
    assert "Formada:" not in listing and "data_formacao" not in listing


def test_unknown_coalition_is_not_found(con):
    for fn in (core.coligacao, core.coligacao_deputados, core.coligacao_partidos):
        with pytest.raises(core.NotFound):
            fn(con, "XYZ")


# Site views built at sync time


def test_sync_builds_the_site_views(con):
    assert con.execute("select count(*) from deputy_current").fetchone()[0] == 230
    seats = dict(con.execute("select group_acronym, seats from party_seats").fetchall())
    assert seats == KNOWN_SPLIT


# Connection handling


def test_data_source_without_a_file_is_unavailable(tmp_path):
    with pytest.raises(DataUnavailable), DataSource(tmp_path).cursor():
        pass


def test_data_source_reopens_when_current_points_at_a_new_file(tmp_path):
    data_dir = build_site_data(tmp_path / "a")
    now = [0.0]
    source = DataSource(data_dir, check_every=60, clock=lambda: now[0])
    with source.cursor() as c:
        assert c.execute("select tag from _meta").fetchone() == (TAG,)
    other = data_dir / "fiscaliza-other.duckdb"
    con = duckdb.connect(str(other))
    con.execute("create table _meta as select 'data-2026-10-21' as tag")
    con.close()
    tmp = data_dir / "next"
    tmp.symlink_to(other.name)
    os.replace(tmp, data_dir / "current.duckdb")
    now[0] = 30.0  # checked at most once a minute
    with source.cursor() as c:
        assert c.execute("select tag from _meta").fetchone() == (TAG,)
    now[0] = 61.0
    with source.cursor() as c:
        assert c.execute("select tag from _meta").fetchone() == ("data-2026-10-21",)


# Routes


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_estatisticas_route_serves_the_service_payload(site_app, con):
    response = site_app.test_client().get("/api/estatisticas")
    assert response.status_code == 200
    assert response.get_json() == core.estatisticas(con)


def test_estatisticas_route_names_every_party(site_app):
    parties = site_app.test_client().get("/api/estatisticas").get_json()["distribuicao_partidos"]
    assert {p["sigla"]: p["nome"] for p in parties} == {g: f"Grupo {g}" for g in KNOWN_SPLIT}


def test_home_donut_labels_its_slices_with_the_party_acronym():
    # Without nameKey, recharts reads a "name" field the payload does not have and the
    # legend falls back to the slice index (0 to 9).
    dashboard = (ROOT / "frontend" / "src" / "components" / "Dashboard.jsx").read_text()
    pie = re.search(r"<Pie\b(.*?)>", dashboard, re.S).group(1)
    assert re.search(r'\bdataKey="deputados"', pie)
    assert re.search(r'\bnameKey="sigla"', pie)


def test_deputados_route_reads_the_frontend_query(site_app):
    response = site_app.test_client().get("/api/deputados?page=1&per_page=20&active_only=false&search=deputado%20300")
    assert [d["id_cadastro"] for d in response.get_json()["deputados"]] == [300]


def test_routes_404_on_unknown_coalition_and_legislature(site_app):
    client = site_app.test_client()
    assert client.get("/api/coligacoes/XYZ").status_code == 404
    assert client.get("/api/estatisticas?legislatura=XL").status_code == 404


def test_health_shows_the_live_tag_and_source_updated(site_app):
    client = site_app.test_client()
    body = client.get("/api/health").get_json()
    assert body["status"] == "healthy"
    assert body["data"]["tag"] == TAG and body["data"]["source_updated"] == "2026-10-20"
    assert client.get("/api/ready").status_code == 200
    assert client.get("/api/ping").status_code == 200


def test_without_data_health_and_pages_say_so(app, tmp_path):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, tmp_path)
    try:
        client = app.test_client()
        assert client.get("/api/health").status_code == 503
        assert client.get("/api/ready").status_code == 503
        assert client.get("/api/estatisticas").status_code == 503
    finally:
        app.extensions[connection.EXTENSION] = before


def test_ported_routes_are_served_by_the_new_blueprint(app):
    endpoints = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert {endpoints[r].split(".")[0] for r in PORTED_ROUTES} == {"core"}
    assert endpoints["/api/health"].startswith("health.")


@pytest.mark.parametrize(
    "path",
    [
        "app/routes/core.py",
        "app/routes/parties.py",
        "app/routes/activity.py",
        "app/routes/health.py",
        *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "app" / "data").glob("*.py")),
        *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "app" / "services").glob("*.py")),
    ],
)
def test_new_data_layer_has_no_sqlalchemy_or_old_database_import(path):
    tree = ast.parse((ROOT / path).read_text())
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert [n for n in names if n.split(".")[0] in {"sqlalchemy", "flask_sqlalchemy", "database"}] == []
