"""#264: the home page's Decisões do Plenário, on the synthetic day in tests/site_decisions.py.

The cards list exactly the decisions the published rule picks (#263) for the last day with
plenary votes, with the group positions as the AR publishes them: no inferred rows from a
unanimous vote. The Government box only counts initiatives the Government authored.
"""

import duckdb
import pytest

from app.services import decisions
from tests.site_data import build_site_data
from tests.site_decisions import DAY


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("decisions",))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


@pytest.fixture
def body(con):
    return decisions.decisoes_plenario(con)


def _by_id(body):
    return {d["vote_id"]: d for d in body["decisoes"]}


def test_the_cards_are_exactly_the_decisions_the_rule_picks(con, body):
    picked = decisions.latest_decisions(con)
    assert body["data"] == DAY == picked["data"]
    assert [d["vote_id"] for d in body["decisoes"]] == [d["vote_id"] for d in picked["decisoes"]]
    assert [d["vote_id"] for d in body["decisoes"]] == [401, 402, 403, 404]  # 405 is a request


def test_positions_are_the_published_ones_by_group(body):
    rejected = _by_id(body)[401]["posicoes"]
    assert rejected["favor"] == [{"grupo": "CDS-PP", "deputados": None}, {"grupo": "PSD", "deputados": None}]
    assert rejected["abstencao"] == [{"grupo": "IL", "deputados": None}]
    assert [p["grupo"] for p in rejected["contra"]] == ["BE", "CH", "JPP", "L", "PAN", "PCP", "PS"]
    assert rejected["ausentes"] == []


def test_a_count_inside_a_group_keeps_its_number(body):
    split = _by_id(body)[403]["posicoes"]
    assert {"grupo": "PS", "deputados": 1} in split["favor"]
    assert split["abstencao"] == [{"grupo": "PS", "deputados": None}]


def test_a_unanimous_vote_gets_no_inferred_groups(body):
    unanimous = _by_id(body)[402]
    assert unanimous["unanimidade"] is True
    assert unanimous["posicoes"] == {"favor": [], "contra": [], "abstencao": [], "ausentes": []}


def test_titles_lose_the_sources_trailing_whitespace(body):
    assert _by_id(body)[401]["iniciativas"][0]["titulo"] == "Iniciativa 81"


def test_the_government_box_counts_only_government_initiatives(body):
    assert body["governo"] == {"votadas": 2, "aprovadas": 1, "rejeitadas": [401]}


def test_no_plenary_votes_means_an_empty_box():
    c = duckdb.connect()
    c.execute("create table votes (vote_id bigint, date date, body varchar)")
    assert decisions.decisoes_plenario(c) == {
        "data": None,
        "decisoes": [],
        "governo": {"votadas": 0, "aprovadas": 0, "rejeitadas": []},
    }


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_the_route_serves_the_service_payload(site_app, body):
    response = site_app.test_client().get("/api/estatisticas/decisoes")
    assert response.status_code == 200
    assert response.get_json() == body
