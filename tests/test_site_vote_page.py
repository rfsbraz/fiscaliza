"""#191: one page per plenary vote, on the synthetic votes in tests/site_votes.py.

Vote 1 is unanimous with inferred positions only, 2 has a PSD deputy named against and the
count 1-PSD, 5 has no positions and no initiative, 8 decides three initiatives (two listed
twice) and 9 is XVI. The export groups the votes by id range, one file per range, and only
the votes of STATIC_PAGE_LEGISLATURES get a page of their own in the Pages build.
"""

import shutil

import duckdb
import pytest
from flask import Flask

from app.data.connection import init_app
from app.routes.activity import activity_bp
from app.services import votes
from app.services.core import NotFound
from tests.site_data import build_site_data


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("votes",))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def test_a_vote_with_published_positions_and_a_named_deputy(con):
    v = votes.votacao(con, 2)
    assert (v["id"], v["legislatura"], v["data"], v["resultado"], v["unanimidade"]) == (
        2,
        "XVII",
        "2025-09-10",
        "Rejeitado",
        False,
    )
    assert v["fase"] == "Votação na generalidade"
    assert v["posicoes"]["favor"] == [{"grupo": "CDS-PP", "deputados": None}, {"grupo": "PSD", "deputados": None}]
    assert [p["grupo"] for p in v["posicoes"]["abstencao"]] == ["IL", "JPP", "PAN"]
    # The count the AR gives next to the name stays as published, apart from the name.
    assert {"grupo": "PSD", "deputados": 1} in v["posicoes"]["contra"]
    assert v["votos_nomeados"] == [{"nome": "Deputado 2", "grupo": "PSD", "posicao": "contra", "id_cadastro": 2}]
    [ini] = v["iniciativas"]
    assert (ini["id"], ini["tipo"], ini["numero"], ini["titulo"], ini["autoria"]) == (
        62,
        "Projeto de Lei",
        62,
        "Iniciativa 62",
        ["PSD"],
    )
    assert ini["url"].endswith("DetalheIniciativa.aspx?BID=62")


def test_a_unanimous_vote_shows_no_inferred_group_positions(con):
    v = votes.votacao(con, 1)
    assert v["unanimidade"] is True
    assert v["posicoes"] == {"favor": [], "contra": [], "abstencao": [], "ausentes": []}


def test_a_vote_without_positions_or_initiative_still_has_its_page(con):
    v = votes.votacao(con, 5)
    assert v["unanimidade"] is False and v["iniciativas"] == [] and v["fase"] is None
    assert v["descricao"] == "Votação 5"
    assert all(group == [] for group in v["posicoes"].values())


def test_each_initiative_once_and_no_shared_phase_left_out(con):
    v = votes.votacao(con, 8)
    assert [i["id"] for i in v["iniciativas"]] == [68, 69, 70]
    assert v["fase"] == "Votação final global"
    assert v["iniciativas"][1]["autoria"] == []


def test_unknown_and_committee_votes_are_not_found(con):
    for vote_id in (7, 999999, -1):
        with pytest.raises(NotFound):
            votes.votacao(con, vote_id)


def test_non_inscritos_and_independents_are_never_named_dissent(data_dir, tmp_path):
    db = tmp_path / "current.duckdb"
    shutil.copy(data_dir / "current.duckdb", db)
    c = duckdb.connect(str(db))
    c.execute(
        "insert into vote_deputy_dissents by name select 4 as vote_id, 'XVII' as legislature, 'plenary' as body, "
        "'favour' as position, 'Deputado 229' as name, 'Ninsc' as group_code, 229 as cadastro_id, 1 as candidates"
    )
    try:
        assert [d["nome"] for d in votes.votacao(c, 4)["votos_nomeados"]] == ["Deputado 2"]
    finally:
        c.close()


# Grouping by id range


@pytest.mark.parametrize(("vote_id", "group"), [(0, 0), (999, 0), (1000, 1), (193246, 193)])
def test_a_vote_goes_in_the_group_of_its_thousand(vote_id, group):
    assert votes.vote_group(vote_id) == group


def test_groups_hold_every_plenary_vote_once_and_the_same_page(con, monkeypatch):
    monkeypatch.setattr(votes, "VOTE_GROUP", 10)
    groups = votes.votacoes_por_grupo(con)
    ids = [int(i) for g in groups.values() for i in g["votacoes"]]
    plenary = [r[0] for r in con.execute("select vote_id from votes where body = 'plenary' order by 1").fetchall()]
    assert sorted(ids) == plenary
    assert set(groups) == {i // 10 for i in plenary}
    assert all(int(i) // 10 == g for g, payload in groups.items() for i in payload["votacoes"])
    assert groups[0]["votacoes"]["2"] == votes.votacao(con, 2)
    assert "7" not in groups[0]["votacoes"]


# The static page set


def test_only_the_static_legislatures_get_a_page(con):
    pages = votes.paginas(con)
    assert pages["legislaturas"] == ["XVII"]
    xvii = [
        r[0]
        for r in con.execute(
            "select vote_id from votes where body = 'plenary' and legislature = 'XVII' order by 1"
        ).fetchall()
    ]
    assert [p["id"] for p in pages["votacoes"]] == xvii
    assert 9 not in {p["id"] for p in pages["votacoes"]}


def test_a_page_title_names_the_initiative_or_the_day(con):
    by_id = {p["id"]: p for p in votes.paginas(con)["votacoes"]}
    assert by_id[2]["titulo"] == "Projeto de Lei n.º 62/XVII: Iniciativa 62"
    assert by_id[2]["descricao"].startswith("Votação no Plenário a 10/09/2025: Rejeitado. Votação na generalidade.")
    assert by_id[1]["descricao"].startswith("Votação no Plenário a 10/07/2025: Aprovado por unanimidade.")
    assert by_id[5]["titulo"] == "Votação 5"


def test_a_vote_with_no_subject_is_titled_by_its_number_and_day(con):
    v = {**votes.votacao(con, 5), "descricao": None}
    assert votes.page_head(v)[0] == "Votação 5 no Plenário de 05/03/2026"


def test_a_long_title_is_cut_at_a_word():
    title = votes.short_title("palavra " * 30)
    assert len(title) <= votes.TITLE_MAX and title.endswith("…") and "  " not in title


# The route


@pytest.fixture
def client(data_dir):
    app = Flask(__name__)
    app.config["FISCALIZA_DATA_DIR"] = str(data_dir)
    init_app(app)
    app.register_blueprint(activity_bp, url_prefix="/api")
    return app.test_client()


def test_route_answers_a_vote_and_404_for_others(client):
    assert client.get("/api/votacoes/2").get_json()["id"] == 2
    assert client.get("/api/votacoes/999999").status_code == 404
    assert client.get("/api/votacoes/abc").status_code == 404
