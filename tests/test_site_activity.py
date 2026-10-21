"""S8: the agenda page's recent votes and activity stats (F33, F34) on the DuckDB data layer.

Values are checked against the votes, initiatives and interventions in tests/site_agenda.py,
plus the deputy activity in tests/site_data.py where it falls in 2026.
"""

from pathlib import Path

import duckdb
import pytest

from app.services import activity
from tests.site_data import build_site_data


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("deputies", "agenda"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


# Recent votes (F33)


def test_recent_plenary_votes_newest_first_without_committee_votes(con):
    body = activity.votacoes_recentes(con, limite=5)
    assert [v["id"] for v in body["votacoes"]] == [306, 304, 303, 302, 301]
    assert body["total"] == 5


def test_limite_and_legislatura(con):
    assert [v["id"] for v in activity.votacoes_recentes(con, limite=2)["votacoes"]] == [306, 304]
    # XVI: the agenda's 308 and the deputy activity's 105 (tests/site_data.py).
    assert [v["id"] for v in activity.votacoes_recentes(con, legislatura="XVI")["votacoes"]] == [308, 105]


def test_vote_shows_the_initiative_phase_and_result(con):
    votes = {v["id"]: v for v in activity.votacoes_recentes(con)["votacoes"]}
    assert votes[306]["titulo"] == "Iniciativa 53"
    assert votes[306]["descricao"] == "Votação na generalidade"
    assert votes[306]["data"] == "2026-06-10"
    assert votes[306]["resultado"] == "Aprovado"
    # Voted together on two initiatives.
    assert votes[303]["titulo"] == "Iniciativa 53 (e mais 1)"
    # No initiative: the vote's own description is the title.
    assert votes[304]["titulo"] == "Voto de pesar 1" and votes[304]["descricao"] is None
    assert votes[304]["unanime"] is True and votes[303]["unanime"] is False


def test_vote_lists_groups_by_position_as_published(con):
    votes = {v["id"]: v for v in activity.votacoes_recentes(con)["votacoes"]}
    assert votes[303]["favor"] == ["CDS-PP", "PS (2)", "PSD"]
    assert votes[303]["contra"] == ["CH", "PS"]
    assert votes[303]["abstencao"] == ["IL"]
    assert votes[303]["ausentes"] == []
    assert votes[306]["ausentes"] == ["CH"] and len(votes[306]["favor"]) == 9
    assert votes[304]["favor"] == votes[304]["contra"] == []


def test_no_per_deputy_counts_are_sent(con):
    vote = activity.votacoes_recentes(con)["votacoes"][0]
    assert not {"votos_favor", "votos_contra", "abstencoes", "ausencias"} & set(vote)


def test_summary_counts_the_votes_shown(con):
    resumo = activity.votacoes_recentes(con, limite=5)["resumo"]
    assert (resumo["aprovadas"], resumo["rejeitadas"]) == (4, 1)
    assert resumo["periodo"] == "Legislatura XVII, últimas 5 votações em plenário"


def test_unknown_legislature_is_not_found(con):
    with pytest.raises(activity.NotFound):
        activity.votacoes_recentes(con, legislatura="XL")


# Activity stats (F34)


def test_activity_counts_the_year_of_the_reference_day(con):
    body = activity.estatisticas_atividade(con)
    stats = body["estatisticas"]
    assert body["periodo"] == "2026"
    assert body["ultima_atualizacao"] == "2026-10-20"
    # Plenary days with a vote or an intervention: 01-15, 02-05, 03-20, 05-05, 06-10, and the
    # deputy activity's 09-16, 09-17 and 09-18 (tests/site_data.py).
    assert stats["sessoes_plenarias"] == {"total_ano": 8}
    assert stats["votacoes"] == {"total_ano": 4, "aprovadas": 3, "rejeitadas": 1, "taxa_aprovacao": 75.0}
    assert stats["iniciativas"] == {"apresentadas": 3}
    # 3 agenda interventions and 4 from the deputy activity.
    assert stats["intervencoes"] == {"total": 7}


def test_figures_without_a_source_are_left_out_not_zero(con):
    stats = activity.estatisticas_atividade(con)["estatisticas"]
    assert "assiduidade" not in stats
    assert "comissoes" not in stats


# Routes


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_routes_serve_the_service_payloads(site_app, con):
    client = site_app.test_client()
    response = client.get("/api/votacoes/recentes?limite=5")
    assert response.status_code == 200
    assert response.get_json() == activity.votacoes_recentes(con, limite=5)
    response = client.get("/api/estatisticas/atividade")
    assert response.status_code == 200
    assert response.get_json() == activity.estatisticas_atividade(con)
    assert client.get("/api/votacoes/recentes?legislatura=XL").status_code == 404


def test_routes_are_served_by_the_activity_blueprint(app):
    endpoints = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert endpoints["/api/votacoes/recentes"].startswith("activity.")
    assert endpoints["/api/estatisticas/atividade"].startswith("activity.")


# Agenda page component

AGENDA_PAGE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "AgendaPage.jsx"
PANEL_STATE = {"hoje": "agendaHoje", "semana": "agendaSemana", "votacoes": "votacoesRecentes"}


def test_agenda_panels_load_and_fail_on_their_own():
    # Today and the week stay on the old code until the agenda mart lands (S13), so one failed
    # request must not throw away the votes and the stats.
    source = AGENDA_PAGE.read_text()
    assert "Promise.all(" not in source
    assert "Promise.allSettled(" in source
    for endpoint in ("agenda/hoje", "agenda/semana", "votacoes/recentes?limite=5", "estatisticas/atividade"):
        assert f"'{endpoint}'" in source
    for panel in ("hoje", "semana", "votacoes"):
        assert f"activeTab === '{panel}' && !{PANEL_STATE[panel]} && <PainelIndisponivel" in source


def test_agenda_page_has_no_demo_data_banner():
    source = AGENDA_PAGE.read_text()
    assert "Dados Demonstrativos" not in source
    assert "simulados" not in source
