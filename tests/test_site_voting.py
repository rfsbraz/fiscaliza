"""S6: voting analytics for deputies and parties on the DuckDB data layer.

Values are checked against the synthetic votes in tests/site_votes.py. Deputy positions come
from deputy_vote_positions, built at sync time: the group's position on the vote day,
overridden when the deputy is named in the detail.
"""

import ast
from pathlib import Path

import duckdb
import pytest
from flask import Flask

from app.data.connection import init_app
from app.routes.voting import voting_bp
from app.services import core, voting
from tests.site_data import build_site_data

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def _positions(con, cadastro_id, legislature="XVII"):
    return dict(
        con.execute(
            "select vote_id, position from deputy_vote_positions where cadastro_id = ? and legislature = ?",
            [cadastro_id, legislature],
        ).fetchall()
    )


# deputy_vote_positions, built at sync time (F16)


def test_position_is_the_group_position_overridden_by_a_named_deputy(con):
    assert _positions(con, 1) == {
        1: "favour",
        2: "favour",
        3: "favour",
        4: "favour",
        5: None,
        6: "absent",
        8: "against",
    }
    assert _positions(con, 2)[2] == "against"
    assert _positions(con, 2)[4] == "abstention"


def test_committee_votes_are_not_deputy_positions(con):
    assert con.execute("select count(*) from deputy_vote_positions where vote_id = 7").fetchone()[0] == 0


def test_only_deputies_seated_on_the_vote_day_get_a_row(con):
    # 231 resigned at the end of 2025 and 232 took the seat; 500 never sat.
    assert sorted(_positions(con, 231)) == [1, 2, 3]
    assert sorted(_positions(con, 232)) == [4, 5, 6, 8]
    assert _positions(con, 500) == {}
    seated = con.execute("select count(*) from deputy_vote_positions where vote_id = 4").fetchone()[0]
    assert seated == 230


def test_a_group_split_by_unnamed_counts_leaves_its_deputies_unknown(con):
    assert _positions(con, 150)[3] is None
    assert _positions(con, 150)[2] == "against"


def test_tallies_add_the_groups_seats_counts_and_named_deputies(con):
    rows = con.execute(
        "select vote_id, favour, against, abstention, absent, complete from vote_tallies order by vote_id"
    ).fetchall()
    tallies = {r[0]: r[1:] for r in rows}
    assert tallies[2] == (90, 129, 11, 0, True)
    assert tallies[3] == (103, 67, 60, 0, True)
    assert tallies[4] == (111, 118, 1, 0, True)
    assert tallies[5][-1] is False


# Deputy voting analytics (F16, F17, F19)


def test_deputy_distribution_counts_known_positions_only(con):
    data = voting.deputado_voting_analytics(con, 1)
    assert data["legislatura"] == "XVII"
    assert data["vote_distribution"] == {"favor": 4, "contra": 1, "abstencao": 0, "ausente": 1}
    assert data["data_sources"]["votes_counted"] == 6
    assert data["data_sources"]["votes_left_out"] == 1
    assert "1" in data["data_sources"]["note"]


def test_deputy_alignment_with_group_counts_votes_both_cast(con):
    discipline = voting.deputado_voting_analytics(con, 1)["party_discipline"]
    assert discipline["aligned_votes"] == 4
    assert discipline["total_votes"] == 5
    assert discipline["overall_alignment"] == 0.8
    assert discipline["monthly"] == [
        {"month": "2025-07", "aligned_votes": 1, "total_votes": 1},
        {"month": "2025-09", "aligned_votes": 1, "total_votes": 1},
        {"month": "2025-11", "aligned_votes": 1, "total_votes": 1},
        {"month": "2026-02", "aligned_votes": 1, "total_votes": 1},
        {"month": "2026-05", "aligned_votes": 0, "total_votes": 1},
    ]


def test_deputy_participation_by_day(con):
    timeline = voting.deputado_voting_analytics(con, 1)["participation_timeline"]
    assert [d["date"] for d in timeline] == [
        "2025-07-10",
        "2025-09-10",
        "2025-11-20",
        "2026-02-10",
        "2026-04-10",
        "2026-05-04",
    ]
    absent = timeline[4]
    assert (absent["total_votes"], absent["participated"], absent["participation_rate"]) == (1, 0, 0.0)
    assert timeline[5]["contra_votes"] == 1


def test_deputy_alignment_with_other_groups_lists_groups_by_acronym(con):
    collab = voting.deputado_voting_analytics(con, 1)["cross_party_collaboration"]
    by_group = {c["party"]: (c["aligned_votes"], c["total_votes"], c["alignment_rate"]) for c in collab}
    assert "PSD" not in by_group
    assert by_group["CH"] == (1, 5, 0.2)
    assert by_group["PS"] == (2, 5, 0.4)
    assert by_group["CDS-PP"] == (4, 5, 0.8)
    assert [c["party"] for c in collab] == sorted(by_group)


def test_deputy_dissent_list_is_votes_named_against_their_group(con):
    dissents = voting.deputado_voting_analytics(con, 1)["dissent_votes"]
    assert [(d["vote_id"], d["voto"], d["voto_grupo"]) for d in dissents] == [(8, "contra", "favor")]
    assert dissents[0]["resultado"] == "aprovada"
    assert dissents[0]["vote_breakdown"]["PS"] == "contra"
    two = voting.deputado_voting_analytics(con, 2)["dissent_votes"]
    assert [d["vote_id"] for d in two] == [4, 2]


def test_absence_is_not_a_dissent(con):
    assert 6 not in [d["vote_id"] for d in voting.deputado_voting_analytics(con, 1)["dissent_votes"]]


def test_close_votes_are_decided_by_ten_or_fewer(con):
    close = voting.deputado_voting_analytics(con, 1)["close_votes"]
    assert [(v["vote_id"], v["voto"], v["votos_favor"], v["votos_contra"]) for v in close] == [(4, "favor", 111, 118)]
    assert close[0]["resultado"] == "rejeitada"


def test_deputy_left_out_votes_include_split_groups(con):
    data = voting.deputado_voting_analytics(con, 150)
    assert data["data_sources"]["votes_counted"] == 5
    assert data["data_sources"]["votes_left_out"] == 2


def test_deputy_defaults_to_their_latest_legislature_and_takes_another(con):
    xvi = voting.deputado_voting_analytics(con, 1, "XVI")
    assert xvi["deputy_info"]["party"]["sigla"] == "PS"
    assert xvi["vote_distribution"]["favor"] == 1
    assert xvi["data_sources"]["votes_left_out"] == 14
    assert voting.deputado_voting_analytics(con, 1, "17")["legislatura"] == "XVII"
    assert voting.deputado_voting_analytics(con, 1)["deputy_info"]["party"]["sigla"] == "PSD"


def test_unknown_deputy_or_legislature_is_not_found(con):
    with pytest.raises(core.NotFound):
        voting.deputado_voting_analytics(con, 500)
    with pytest.raises(core.NotFound):
        voting.deputado_voting_analytics(con, 999999)
    with pytest.raises(core.NotFound):
        voting.deputado_voting_analytics(con, 300, "XVII")


def test_dropped_deputy_keys_are_gone(con):
    data = voting.deputado_voting_analytics(con, 1)
    for key in ("theme_analysis", "critical_votes"):
        assert key not in data
    assert "budget_votes" not in data["data_sources"]


# Party voting analytics (F25 to F29)


def test_party_monthly_votes_and_initiatives(con):
    months = voting.partido_voting_analytics(con, "PSD")["temporal_behavior"]
    assert [m["date"] for m in months] == ["2025-07", "2025-09", "2025-11", "2026-02", "2026-04", "2026-05"]
    first = months[0]
    assert (first["total_votes"], first["favor_votes"], first["initiatives"]) == (1, 1, 4)
    april = months[4]
    assert (april["favor_votes"], april["abstention_votes"], april["against_votes"]) == (0, 1, 0)


def test_party_outcomes_by_type_over_decided_initiatives(con):
    data = voting.partido_voting_analytics(con, "PSD", "XVI")
    by_type = {t["type_code"]: t for t in data["legislative_effectiveness"]["by_type"]}
    j = by_type["J"]
    assert (j["initiated"], j["approved"], j["partly_approved"], j["rejected"], j["undecided"]) == (12, 8, 1, 3, 1)
    assert j["approval_rate"] == round(8 / 11, 3)
    # Fewer than 10 decided: counts only, no rate.
    assert (by_type["R"]["approved"], by_type["R"]["rejected"], by_type["R"]["approval_rate"]) == (1, 1, None)
    assert [t["type_code"] for t in data["legislative_effectiveness"]["by_type"]] == ["J", "R"]


def test_joint_initiatives_count_for_each_group(con):
    ps = voting.partido_voting_analytics(con, "PS", "XVI")["legislative_effectiveness"]["by_type"]
    assert [(t["type_code"], t["initiated"], t["approved"]) for t in ps] == [("J", 1, 1)]


def test_party_cohesion_by_initiative_type(con):
    cohesion = {c["type_code"]: c for c in voting.partido_voting_analytics(con, "PSD")["cohesion_by_theme"]}
    assert (cohesion["J"]["total_votes"], cohesion["J"]["cohesive_votes"], cohesion["J"]["cohesion_score"]) == (
        4,
        1,
        0.25,
    )
    assert cohesion["R"]["cohesion_score"] == 1.0
    assert cohesion["J"]["tema"] == "Projeto de Lei"


def test_party_agreement_with_other_groups(con):
    patterns = voting.partido_voting_analytics(con, "PSD")["coalition_patterns"]
    by_group = {p["party"]: (p["aligned_votes"], p["total_votes"]) for p in patterns}
    assert by_group["CH"] == (2, 6)
    assert by_group["CDS-PP"] == (5, 6)
    assert by_group["PS"] == (1, 6)
    assert "PSD" not in by_group
    assert [p["party"] for p in patterns] == sorted(by_group)


def test_party_participation_metrics(con):
    metrics = voting.partido_voting_analytics(con, "PSD")["participation_metrics"]
    assert metrics["total_initiatives"] == 4
    assert metrics["total_interventions"] == 2
    assert metrics["total_votes_participated"] == 6
    assert metrics["interventions_note"]
    assert voting.partido_voting_analytics(con, "PSD", "XVI")["participation_metrics"]["interventions_note"] is None


def test_party_takes_the_arabic_legislature_number_the_page_sends(con):
    assert voting.partido_voting_analytics(con, "PSD", "17")["legislatura"] == "XVII"


def test_unknown_party_is_not_found(con):
    with pytest.raises(core.NotFound):
        voting.partido_voting_analytics(con, "XYZ")
    with pytest.raises(core.NotFound):
        voting.partido_voting_analytics(con, "JPP", "XVI")


def test_dropped_party_keys_are_gone(con):
    data = voting.partido_voting_analytics(con, "PSD")
    assert "ideological_positioning" not in data
    for key in ("bills_initiated", "bills_passed", "success_rate"):
        assert key not in data["legislative_effectiveness"]


# Routes


def test_voting_routes_have_no_sqlalchemy(con):
    source = (ROOT / "app" / "routes" / "voting.py").read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [node.module or ""] + [a.name for a in node.names]
            assert not any("sqlalchemy" in n or n.startswith("database") for n in names)
    legacy = (ROOT / "app" / "routes" / "parlamento.py").read_text()
    assert "voting-analytics" not in legacy


def test_voting_routes_serve_json(data_dir):
    app = Flask(__name__)
    app.register_blueprint(voting_bp, url_prefix="/api")
    init_app(app, data_dir)
    client = app.test_client()
    assert client.get("/api/deputados/1/voting-analytics?legislatura=XVII").get_json()["legislatura"] == "XVII"
    assert client.get("/api/partidos/CDS-PP/voting-analytics?legislatura=17").status_code == 200
    assert client.get("/api/deputados/999999/voting-analytics").status_code == 404
    assert client.get("/api/partidos/XYZ/voting-analytics").status_code == 404
