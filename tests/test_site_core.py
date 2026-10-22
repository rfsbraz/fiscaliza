"""S4: the DuckDB repository, site views and the core pages it serves.

Values are checked against the synthetic release in tests/site_data.py: XVII has 230 seats
with the known split, a mid-term replacement and a substitute who never sat.
"""

import ast
import os
import re
import shutil
from pathlib import Path

import duckdb
import pytest

from app.data.connection import DataSource, DataUnavailable
from app.services import core
from tests.site_data import AD_ACORES, ELECTED_UNMATCHED, EXTRACT, KNOWN_SPLIT, TAG, build_site_data

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


def test_a_current_mandate_needs_a_seat_in_the_current_legislature(con):
    # #107: an election without a seat is not a mandate. 501 and 302 were elected to XVII and never
    # sat in it (302 sat in XVI); 303 sat in XVII for a day and is suspended now; 1 is seated; 300
    # sat only in XVI.
    def career(cad):
        found = core.deputados(con, search=f"deputado {cad}", active_only=False, per_page=100)["deputados"]
        return next(d["career_info"] for d in found if d["id_cadastro"] == cad)

    assert career(501)["seated_in_current_legislature"] is False
    assert career(302)["seated_in_current_legislature"] is False
    assert career(303)["seated_in_current_legislature"] is True
    assert career(1)["seated_in_current_legislature"] is True
    assert career(300)["seated_in_current_legislature"] is False


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


# Coalitions (F31). One page per list and run (#111): a list that won seats in more than one
# circle (or in a legislature with no seats per circle) joins the coalition's run of consecutive
# legislatures; a list that won seats only in the Açores or Madeira is a page of its own.


def _list_seats(con, ballot, legislature="XVII"):
    return con.execute(
        "select sum(seats) from ballot_list_seats where legislature = ? and ballot_acronym = ?", [legislature, ballot]
    ).fetchone()[0]


def test_coalitions_active_by_default(con):
    listed = core.coligacoes(con)["coligacoes"]
    assert [(c["id"], c["sigla"]) for c in listed] == [("ad-2024", "AD"), ("ad-acores-2025", "AD"), ("CDU", "CDU")]
    every = {c["id"]: c for c in core.coligacoes(con, include_inactive=True)["coligacoes"]}
    assert sorted(every) == ["CDU", "FRS", "ad-2024", "ad-acores-2025"]
    assert every["FRS"]["ativa"] is False and every["FRS"]["data_dissolucao"] == "2025-06-02"
    assert every["ad-2024"]["ativa"] is True and every["ad-2024"]["data_dissolucao"] is None
    assert every["ad-2024"]["data_formacao"] == "2024-03-26"
    assert every["ad-acores-2025"]["data_formacao"] == "2025-06-03"


def test_each_list_and_run_is_its_own_page(con):
    # #111: the page grouped every AD list under one short name, so it added the Açores list
    # to the national one (88 + 3 in production).
    national = core.coligacao(con, "ad-2024")
    acores = core.coligacao(con, "ad-acores-2025")
    assert national["deputy_count"] == _list_seats(con, "AD-LISTA")
    assert acores["deputy_count"] == _list_seats(con, "AD-ACORES")
    assert national["deputy_count"] + acores["deputy_count"] == AD_XVII_SCOPED
    assert (national["ambito"], national["eleicoes"]) == (None, [2024, 2025])
    assert (acores["ambito"], acores["eleicoes"]) == ("Açores", [2025])
    assert [p["sigla"] for p in national["component_parties"]] == ["PSD", "CDS-PP"]
    assert [(p["sigla"], p["com_lugares"]) for p in acores["component_parties"]] == [
        ("PSD", True),
        ("CDS-PP", True),
        ("PPM", False),
    ]
    xvi, xvii = _list_seats(con, "AD-LISTA", "XVI"), _list_seats(con, "AD-LISTA")
    assert national["legislaturas"] == [
        {
            "legislatura": "XVI",
            "ano_eleicao": 2024,
            "listas": ["AD-LISTA"],
            "deputados": xvi,
            "em_funcoes": xvi,
            "contagem": "eleitos",
        },
        {
            "legislatura": "XVII",
            "ano_eleicao": 2025,
            "listas": ["AD-LISTA"],
            "deputados": xvii,
            "em_funcoes": xvii,
            "contagem": "eleitos",
        },
    ]
    n = acores["deputy_count"]
    assert acores["legislaturas"] == [
        {
            "legislatura": "XVII",
            "ano_eleicao": 2025,
            "listas": ["AD-ACORES"],
            "deputados": n,
            "em_funcoes": n,
            "contagem": "eleitos",
        }
    ]
    assert {d["circulo"] for d in core.coligacao_deputados(con, "ad-acores-2025")["deputados"]} == {"Açores"}
    assert "Açores" not in {d["circulo"] for d in core.coligacao_deputados(con, "ad-2024")["deputados"]}


def test_page_ids_follow_the_approved_slugs():
    # The real seed's AD and Madeira Primeiro lists, with the circles where each won seats
    # (None for a legislature with no seats per circle, as Constituinte and I-A).
    order = ["I-A", "I-B", "II", "III", "XIII", "XIV", "XV", "XVI", "XVII"]
    nation = {"Lisboa", "Porto", "Açores"}
    lists = [
        ("AD", "I-B", "AD", None, 1979),
        ("AD", "II", "AD", None, 1980),
        ("AD", "XV", "PPD/PSD.CDS-PP.PPM", {"Açores"}, 2022),
        ("AD", "XVI", "PPD/PSD.CDS-PP.PPM", nation, 2024),
        ("AD", "XVII", "PPD/PSD.CDS-PP", {"Lisboa", "Porto", "Madeira"}, 2025),
        ("AD", "XVII", "PPD/PSD.CDS-PP.PPM", {"Açores"}, 2025),
        ("Madeira Primeiro", "XV", "PPD/PSD.CDS-PP", {"Madeira"}, 2022),
        ("Madeira Primeiro", "XVI", "PPD/PSD.CDS-PP", {"Madeira"}, 2024),
        ("PàF", "XIII", "PPD/PSD.CDS-PP", {"Lisboa", "Porto"}, 2015),
        ("CDU", "XIII", "PCP-PEV", {"Lisboa"}, 2015),
        ("CDU", "XIV", "PCP-PEV", {"Lisboa", "Porto"}, 2019),
    ]
    pages = core.coalition_pages(
        order,
        [
            dict(zip(("coalition", "legislature", "ballot_acronym", "circles", "election_year"), x, strict=True))
            for x in lists
        ],
    )
    found = {p["id"]: (p["ambito"], p["legislaturas"]) for p in pages}
    assert found == {
        "ad-1979": (None, ["I-B", "II"]),
        "ad-acores-2022": ("Açores", ["XV"]),
        "ad-2024": (None, ["XVI", "XVII"]),
        "ad-acores-2025": ("Açores", ["XVII"]),
        "madeira-primeiro-2022": ("Madeira", ["XV"]),
        "madeira-primeiro-2024": ("Madeira", ["XVI"]),
        "PàF": (None, ["XIII"]),
        # A national list that won seats in one circle stays national.
        "CDU": (None, ["XIII", "XIV"]),
    }


def test_coalition_detail_deputies_and_parties(con):
    assert core.coligacao(con, "ad-2024")["nome"] == "Coligação AD"
    deputies = core.coligacao_deputados(con, "ad-2024")["deputados"]
    assert len(deputies) == _list_seats(con, "AD-LISTA")
    assert {d["partido_sigla"] for d in deputies} == {"PSD", "CDS-PP"}
    assert [p["sigla"] for p in core.coligacao_partidos(con, "ad-acores-2025")["partidos"]] == ["PSD", "CDS-PP", "PPM"]
    assert core.coligacao_partidos(con, "ad-2024")["coligacao"]["id"] == "ad-2024"
    assert (
        len(core.coligacao_deputados(con, "FRS")["deputados"]) == 27
    )  # FRS ran in XVI only: PS there, person 1 included


def test_coalition_is_found_by_its_path_form(con):
    # The static export serves coligacoes/<slug(id)>.json; Flask answers the same ids.
    assert core.coligacao(con, "cdu")["id"] == "CDU"
    assert core.coligacao(con, "AD-2024")["id"] == "ad-2024"


def test_the_old_merged_coalition_is_gone(con):
    for fn in (core.coligacao, core.coligacao_deputados, core.coligacao_partidos):
        with pytest.raises(core.NotFound):
            fn(con, "AD")


# PSD and CDS-PP hold seats 1 to 91 in XVII (KNOWN_SPLIT), in circle cad % 22 + 1. AD's two lists
# won seats in circles 1 to 20 (ballot_list_seats), so the 8 of them in circles 21 and 22 are out.
AD_XVII_SCOPED = 83


def test_coalition_deputies_come_only_from_circles_where_its_lists_won_seats(con):
    # #181: every deputy of the coalition's groups was counted, whatever their circle.
    circles = {
        d["circulo"] for page in ("ad-2024", "ad-acores-2025") for d in core.coligacao_deputados(con, page)["deputados"]
    }
    assert "Círculo 21" not in circles and "Círculo 22" not in circles
    expected = {f"Círculo {i}" for i in range(1, 21) if i != 19} | {"Açores"}
    assert circles == expected  # circle 5's "a)" mark is ignored
    ad_seats = con.execute(
        "select sum(seats) from ballot_list_seats where legislature = 'XVII' and ballot_acronym in ('AD-LISTA', 'AD-ACORES')"
    ).fetchone()[0]
    assert ad_seats == AD_XVII_SCOPED
    listed = {c["id"]: c for c in core.coligacoes(con)["coligacoes"]}
    assert listed["ad-2024"]["deputy_count"] + listed["ad-acores-2025"]["deputy_count"] == AD_XVII_SCOPED
    assert len(core.coligacao_deputados(con, "CDU")["deputados"]) == KNOWN_SPLIT["PCP"]


def test_every_coalition_list_has_exactly_its_seats_in_each_legislature(con):
    # #181 pre-XI: the release has seats per circle and list from I-B on, so the circle rule
    # holds in XVI as in XVII. PSD and CDS-PP deputies of circles 21 and 22 are out in both.
    for page, ballot in [
        ("ad-2024", "AD-LISTA"),
        ("ad-acores-2025", AD_ACORES),
        ("CDU", "CDU-LISTA"),
        ("FRS", "FRS-LISTA"),
    ]:
        detail = core.coligacao(con, page)
        for leg in detail["legislaturas"]:
            listed = core.coligacao_deputados(con, page, leg["legislatura"])["total_deputados"]
            assert listed == leg["deputados"] == _list_seats(con, ballot, leg["legislatura"]), (page, leg)
    xvi = core.coligacao_deputados(con, "ad-2024", "XVI")["deputados"]
    assert not {"Círculo 21", "Círculo 22"} & {d["circulo"] for d in xvi}
    seated = con.execute(
        "select count(*) from seated_detail(date '2025-06-02') "
        "where legislature = 'XVI' and group_acronym in ('PSD', 'CDS-PP')"
    ).fetchone()[0]
    assert len(xvi) < seated
    assert core.coligacao_deputados(con, "FRS")["total_deputados"] == 27


def test_coalition_deputies_keep_the_group_rule_without_seats_per_circle(data_dir, tmp_path):
    # A legislature with no ballot_list_seats rows (Constituinte and I-A in the release): all
    # deputies of the coalition's groups count there. XVI is emptied here to stand for one.
    path = tmp_path / "no-seats.duckdb"
    shutil.copy(data_dir / "current.duckdb", path)
    c = duckdb.connect(str(path))
    try:
        c.execute("delete from ballot_list_seats where legislature = 'XVI'")
        c.execute("delete from ballot_list_elected where legislature = 'XVI'")
        assert c.execute("select count(*) from ballot_list_seats where legislature = 'XVI'").fetchone()[0] == 0
        xvi = core.coligacao_deputados(c, "ad-2024", "XVI")
        seated = c.execute(
            "select count(*) from seated_detail(date '2025-06-02') "
            "where legislature = 'XVI' and group_acronym in ('PSD', 'CDS-PP')"
        ).fetchone()[0]
        assert xvi["legislatura"] == "XVI" and xvi["total_deputados"] == seated > 0
        assert {"Círculo 21", "Círculo 22"} <= {d["circulo"] for d in xvi["deputados"]}
        assert core.coligacao_deputados(c, "ad-2024")["total_deputados"] == _list_seats(c, "AD-LISTA")
        legs = {leg["legislatura"]: leg for leg in core.coligacao(c, "ad-2024")["legislaturas"]}
        assert legs["XVI"]["contagem"] == "em_funcoes" and legs["XVI"]["deputados"] == seated
        assert legs["XVII"]["contagem"] == "eleitos"
    finally:
        c.close()


# #197: a coalition page counts the deputies elected on its lists, as the election result has
# them. Up to VI the release lists them (ballot_list_elected, XVI in the fixture); from VII on the
# mandates give them: a mandate from the legislature's first day as Efetivo, Suspenso(Eleito) or
# Renunciou, on the list of the person's first group in a circle where that list won seats (XVII
# in the fixture). Who held the seat on the legislature's last day is a second figure.


def _move_to_ch(c, legislature, cad, day):
    """Move a deputy to CH from ``day`` on, as a deputy who leaves the coalition's group."""
    end = c.execute(
        "select end_date from group_memberships where legislature = ? and cadastro_id = ?", [legislature, cad]
    ).fetchone()[0]
    c.execute(
        "update group_memberships set end_date = ?::date - 1, is_open = false where legislature = ? and cadastro_id = ?",
        [day, legislature, cad],
    )
    c.execute(
        "insert into group_memberships values (?, ?, 2, 'CH', ?, ?, ?)", [legislature, cad, day, end, end is None]
    )


def _ad_deputy(c, legislature, day):
    return c.execute(
        "select min(cadastro_id) from seated_detail(?::date) where legislature = ? and group_acronym = 'PSD' "
        "and circle = 'Círculo 3'",
        [day, legislature],
    ).fetchone()[0]


def test_coalition_count_is_the_deputies_elected_on_its_lists(data_dir, tmp_path):
    path = tmp_path / "moved.duckdb"
    shutil.copy(data_dir / "current.duckdb", path)
    c = duckdb.connect(str(path))
    try:
        xvi_cad = _ad_deputy(c, "XVI", "2025-06-02")
        xvii_cad = _ad_deputy(c, "XVII", EXTRACT)
        _move_to_ch(c, "XVI", xvi_cad, "2025-01-01")
        _move_to_ch(c, "XVII", xvii_cad, "2026-01-01")
        xvi, xvii = _list_seats(c, "AD-LISTA", "XVI"), _list_seats(c, "AD-LISTA")
        detail = core.coligacao(c, "ad-2024")
        legs = {leg["legislatura"]: leg for leg in detail["legislaturas"]}
        assert (legs["XVI"]["deputados"], legs["XVI"]["em_funcoes"]) == (xvi, xvi - 1)
        assert (legs["XVII"]["deputados"], legs["XVII"]["em_funcoes"]) == (xvii, xvii - 1)
        assert (detail["deputy_count"], detail["deputados_em_funcoes"]) == (xvii, xvii - 1)
        assert (detail["contagem"], detail["legislatura_aberta"], detail["data_em_funcoes"]) == (
            "eleitos",
            True,
            EXTRACT,
        )
        listed = {x["id"]: x for x in core.coligacoes(c)["coligacoes"]}["ad-2024"]
        assert (listed["deputy_count"], listed["deputados_em_funcoes"]) == (xvii, xvii - 1)
        for leg, cad, seats in (("XVI", xvi_cad, xvi), ("XVII", xvii_cad, xvii)):
            page = core.coligacao_deputados(c, "ad-2024", leg)
            assert page["total_deputados"] == len(page["deputados"]) == seats
            moved = [d for d in page["deputados"] if d["id_cadastro"] == cad]
            assert [d["partido_sigla"] for d in moved] == ["PSD"], leg  # the group they were elected for
        frs = core.coligacao(c, "FRS")
        assert (frs["legislatura_aberta"], frs["data_em_funcoes"]) == (False, "2025-06-02")
    finally:
        c.close()


def test_elected_rows_without_a_cadastro_id_still_count(con):
    # The release could not match one published name of the XVI AD list to a deputy.
    page = core.coligacao_deputados(con, "ad-2024", "XVI")
    assert page["total_deputados"] == len(page["deputados"]) == _list_seats(con, "AD-LISTA", "XVI")
    unmatched = [d for d in page["deputados"] if d["id_cadastro"] is None]
    assert unmatched == [
        {
            "id": None,
            "id_cadastro": None,
            "nome": ELECTED_UNMATCHED,
            "nome_completo": ELECTED_UNMATCHED,
            "partido_sigla": None,
            "circulo": "Círculo 2",
            "picture_url": None,
        }
    ]


def test_the_list_and_the_mandates_give_the_same_elected(data_dir, tmp_path):
    # A release without ballot_list_elected (before schema 1.6.0) takes the mandates for XVI too,
    # and both ways give each list exactly its seats.
    path = tmp_path / "no-elected.duckdb"
    shutil.copy(data_dir / "current.duckdb", path)
    c = duckdb.connect(str(path))
    try:
        from_list = {d["id_cadastro"] for d in core.coligacao_deputados(c, "ad-2024", "XVI")["deputados"]}
        c.execute("drop table ballot_list_elected")
        for page, ballot in [("ad-2024", "AD-LISTA"), ("CDU", "CDU-LISTA"), ("FRS", "FRS-LISTA")]:
            for leg in core.coligacao(c, page)["legislaturas"]:
                assert leg["deputados"] == _list_seats(c, ballot, leg["legislatura"]), (page, leg)
        from_mandates = {d["id_cadastro"] for d in core.coligacao_deputados(c, "ad-2024", "XVI")["deputados"]}
        assert len(from_mandates - from_list) == 1 and from_list - from_mandates == {None}
    finally:
        c.close()


def test_coalition_parties_without_seats_are_marked(con):
    # #181: PPM ran on the Açores AD list and PEV on the CDU list without winning a seat.
    detail = core.coligacao(con, "ad-acores-2025")["component_parties"]
    assert [(p["sigla"], p["com_lugares"]) for p in detail] == [("PSD", True), ("CDS-PP", True), ("PPM", False)]
    parties = core.coligacao_partidos(con, "CDU")["partidos"]
    assert [(p["sigla"], p["com_lugares"]) for p in parties] == [("PCP", True), ("PEV", False)]
    for page in ("ColigacaoDetalhes.jsx", "PartidosPage.jsx"):
        assert "seatsNote(" in (ROOT / "frontend" / "src" / "components" / page).read_text(), page


def test_coalition_pages_link_by_id_and_show_scope_and_legislatures():
    # Two AD cards and two AD pages: the link is the page id, the card and the header say
    # which list and elections it is, and the page lists its legislatures.
    detail = (ROOT / "frontend" / "src" / "components" / "ColigacaoDetalhes.jsx").read_text()
    listing = (ROOT / "frontend" / "src" / "components" / "PartidosPage.jsx").read_text()
    party = (ROOT / "frontend" / "src" / "components" / "PartidoDetalhes.jsx").read_text()
    for page in (detail, listing):
        assert "coalitionScope(" in page
    assert "coligacao.sigla)}" not in listing and "/coligacoes/${encodeURIComponent(coligacao.id)}" in listing
    assert "/coligacoes/${encodeURIComponent(dados.coligacao.id)}" in party
    assert "dados.legislaturas" in detail and "Primeira legislatura com deputados eleitos" in detail


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
