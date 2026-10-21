"""S5: the deputy page (detalhes, atividades, conflitos-interesse) on the DuckDB data layer.

Values are checked against the synthetic release in tests/site_data.py. Person 1 sat for PS in
XVI and for PSD in XVII, authored initiatives in both (one with person 90 of CH), spoke in both,
and has two interest declarations from XV.
"""

import ast
from datetime import date
from pathlib import Path

import duckdb
import pytest

from app.services import core, deputies
from tests.site_data import EXTRACT, build_site_data

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "frontend" / "src" / "components" / "DeputadoDetalhes.jsx"
DEPUTY_ROUTES = {
    "/api/deputados/<int:cad_id>/detalhes",
    "/api/deputados/<int:cad_id>/atividades",
    "/api/deputados/<int:cad_id>/conflitos-interesse",
}


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


# Header and mandate history (F04, F05)


def test_current_deputy_header(con):
    d = deputies.detalhes(con, 1)
    assert (d["id_cadastro"], d["nome"], d["nome_completo"]) == (1, "Deputado 1", "Nome Completo 1")
    assert d["partido"] == {"id": "PSD", "sigla": "PSD", "nome": "Grupo PSD"}
    assert d["circulo"] == "Círculo 2"
    assert d["legislatura"] == {"numero": "XVII", "designacao": "XVII Legislatura", "ativa": True}
    assert d["legislatura_numero"] == "XVII"
    assert d["mandato"]["inicio"] == "2025-06-03"
    assert d["is_seated"] is True and d["mandate_status"] == "Efetivo"
    assert d["career_info"]["is_currently_active"] is True
    assert d["picture_url"].endswith("id=1&type=deputado")
    assert d["sexo"] == "F" and d["profissao"] == "Profissão 1"


def test_mandate_history_newest_first_with_the_group_of_each_legislature(con):
    history = deputies.detalhes(con, 1)["mandatos_historico"]
    assert [(m["legislatura_numero"], m["partido_sigla"], m["is_current"]) for m in history] == [
        ("XVII", "PSD", True),
        ("XVI", "PS", False),
    ]
    assert (history[1]["mandato_inicio"], history[1]["mandato_fim"]) == ("2024-03-26", "2025-06-02")
    assert history[0]["mandato_fim"] is None
    assert history[1]["legislatura_nome"] == "XVI Legislatura"


def test_former_deputy_shows_the_latest_completed_mandate(con):
    d = deputies.detalhes(con, 300)
    assert d["legislatura"]["numero"] == "XVI" and d["legislatura"]["ativa"] is False
    assert d["is_seated"] is False and d["career_info"]["is_currently_active"] is False
    assert d["career_info"]["latest_completed_mandate"] == {"legislatura": "XVI", "periodo": "2024-2025"}


def test_resigned_deputy_is_not_seated(con):
    d = deputies.detalhes(con, 231)
    assert d["is_seated"] is False and d["mandate_status"] == "Renunciou"


def test_unknown_or_never_seated_person_is_not_found(con):
    for cad in (99999, 500):
        with pytest.raises(core.NotFound):
            deputies.detalhes(con, cad)


# Counts, approval rate and comparisons (F06, F07, F08)


def test_counts_across_the_career(con):
    s = deputies.detalhes(con, 1)["estatisticas"]
    assert s["iniciativas_propostas"] == 5
    assert s["intervencoes_parlamentares"] == 8
    assert s["total_mandatos"] == 2
    assert s["legislaturas_servidas"] == "XVI, XVII"
    assert s["nivel_experiencia"] == "Experiente"
    days = (date(2025, 6, 2) - date(2024, 3, 26)).days + (date.fromisoformat(EXTRACT) - date(2025, 6, 3)).days
    assert s["tempo_servico_anos"] == round(days / 365.25, 1)
    assert s["iniciativas_por_tipo"] == [
        {"codigo": "J", "descricao": "Projeto de Lei", "total": 4},
        {"codigo": "R", "descricao": "Projeto de Resolução", "total": 1},
    ]
    assert s["evolucao_legislaturas"] == [
        {"legislatura": "XVII", "iniciativas": 4, "intervencoes": 3},
        {"legislatura": "XVI", "iniciativas": 1, "intervencoes": 5},
    ]


def test_approved_means_the_latest_decisive_plenary_vote_passed(con):
    # 1 passed its final global vote and 5 passed in XVI. 2 lost its deliberation vote, 3 was
    # never voted and 4 only passed on the generality, which does not decide it.
    s = deputies.detalhes(con, 1)["estatisticas"]
    assert s["iniciativas_aprovadas"] == 2
    assert s["taxa_aprovacao"] == 40.0


def test_a_committee_vote_does_not_count_as_approval(con):
    s = deputies.detalhes(con, 2)["estatisticas"]
    assert (s["iniciativas_propostas"], s["iniciativas_aprovadas"], s["taxa_aprovacao"]) == (1, 0, 0.0)


def test_party_average_and_national_percentile_in_the_latest_legislature(con):
    s = deputies.detalhes(con, 1)["estatisticas"]
    # 89 people sat for PSD in XVII: person 1 has 4 initiatives and 3 interventions, person 2 one initiative.
    assert s["iniciativas_legislatura"] == 4 and s["intervencoes_legislatura"] == 3
    assert s["media_partido_iniciativas"] == round(5 / 89, 2)
    assert s["media_partido_intervencoes"] == round(3 / 89, 2)
    assert s["percentil_nacional"] == 100


def test_dropped_and_unavailable_fields(con):
    s = deputies.detalhes(con, 1)["estatisticas"]
    assert "contexto_oposicao" not in s  # F09
    assert s["taxa_assiduidade"] is None  # attendance waits for its mart (S11)


# Interventions and initiatives (F10, F11 without phase)


def test_interventions_of_the_latest_legislature_newest_first(con):
    a = deputies.atividades(con, 1)
    assert a["legislatura"] == {"numero": "XVII", "designacao": "XVII Legislatura"}
    assert [i["data"] for i in a["intervencoes"]] == ["2026-09-18", "2026-09-17", "2026-09-16"]
    first = a["intervencoes"][0]
    assert first["tipo"] == "Declaração politica" and first["assunto"] == "Debate 3"
    assert first["publicacao"] == {
        "pub_tipo": "DAR I série",
        "pub_data": "2026-09-18",
        "pub_numero": 3,
        "paginas": "3-4",
        "url_diario": "https://example.org/dar/3",
    }
    assert a["intervention_metadata"] == {"total": 3, "page": 1, "per_page": 50, "pages": 1}


def test_intervention_averages_of_the_legislature(con):
    # XVI: person 1 has all 5 interventions; 230 people held a seat, 27 of them for PS.
    medias = deputies.atividades(con, 1, "XVI")["medias_intervencoes"]
    assert medias == {"partido": round(5 / 27, 2), "parlamento": round(5 / 230, 2)}
    assert deputies.atividades(con, 300, "XVII")["medias_intervencoes"] == {"partido": None, "parlamento": None}


def test_open_legislature_says_the_interventions_are_incomplete(con):
    note = deputies.atividades(con, 1)["nota_intervencoes"]
    assert "XVII" in note and "4 intervenções" in note
    assert deputies.atividades(con, 1, legislatura="XVI")["nota_intervencoes"] is None


def test_interventions_filter_sort_and_paging(con):
    assert [i["tipo"] for i in deputies.atividades(con, 1, "XVI", tipo="Pergunta")["intervencoes"]] == ["Pergunta"]
    oldest = deputies.atividades(con, 1, "XVI", ordem="oldest")["intervencoes"]
    assert oldest[0]["data"] == "2024-04-10"
    by_type = deputies.atividades(con, 1, "XVI", ordem="type")["intervencoes"]
    assert [i["tipo"] for i in by_type] == sorted(i["tipo"] for i in by_type)
    page = deputies.atividades(con, 1, "XVI", page=2, per_page=2)
    assert len(page["intervencoes"]) == 2
    assert page["intervention_metadata"] == {"total": 5, "page": 2, "per_page": 2, "pages": 3}


def test_initiatives_of_the_legislature_with_their_outcome(con):
    found = {i["id"]: i for i in deputies.atividades(con, 1)["iniciativas"]}
    assert list(found) == [4, 3, 2, 1]
    assert (found[1]["estado"], found[1]["resultado"], found[1]["aprovada"]) == ("Aprovado", "Aprovado", True)
    assert (found[2]["estado"], found[2]["aprovada"]) == ("Rejeitado", False)
    assert found[3]["estado"] is None and found[3]["resultado"] is None
    assert found[4]["autores"] == ["Deputado 1", "Deputado 90"] and found[4]["is_cross_party"] is True
    assert found[1]["autores"] == ["Deputado 1"] and found[1]["is_cross_party"] is False
    assert found[1]["urls"]["documento"] == "https://example.org/1.pdf"
    assert found[1]["urls"]["oficial"].endswith("BID=1")
    assert (found[1]["tipo"], found[1]["tipo_descricao"], found[1]["data"]) == ("J", "Projeto de Lei", "2025-07-01")


def test_legislature_the_deputy_did_not_serve_is_empty(con):
    a = deputies.atividades(con, 300, "XVII")
    assert a["intervencoes"] == [] and a["iniciativas"] == []
    assert a["deputado"]["served_in_legislature"] is False


def test_atividades_unknown_legislature_or_deputy_is_not_found(con):
    with pytest.raises(core.NotFound):
        deputies.atividades(con, 1, "XL")
    with pytest.raises(core.NotFound):
        deputies.atividades(con, 99999)


# Interest register (F13, F14, F15)


def test_latest_declaration_with_activities_and_shareholdings(con):
    c = deputies.conflitos_interesse(con, 1)
    assert c["tem_declaracao"] is True
    assert (c["full_name"], c["legislatura"]) == ("Nome Completo 1", "XV")
    assert c["professional_activities"] == [{"entity_name": "Empresa Exemplo", "function_type": "Consultor"}]
    assert c["shareholdings"] == [{"entity_name": "Sociedade Exemplo", "share_percentage": "10"}]
    assert c["is_exclusive"] is False and c["has_conflict_potential"] is True
    # No sector or legislation matching in the release: the page must not claim any overlap.
    assert c["regulated_sector_count"] is None


def test_xvi_and_xvii_wait_for_the_ept(con):
    ept = deputies.conflitos_interesse(con, 1)["ept"]
    assert ept["pendente"] is True and ept["legislaturas"] == ["XVI", "XVII"]
    assert ept["url"].startswith("https://entidadetransparencia.pt")
    only_xvi = deputies.conflitos_interesse(con, 300)
    assert only_xvi["tem_declaracao"] is False and only_xvi["ept"]["legislaturas"] == ["XVI"]


def test_family_fields_are_gone_for_good(con):
    c = deputies.conflitos_interesse(con, 1)
    for field in ("spouse_name", "spouse_deputy", "marital_status", "matrimonial_regime", "dgf_number"):
        assert field not in c
    source = COMPONENT.read_text()
    for field in ("spouse_name", "spouse_deputy", "marital_status", "matrimonial_regime", "dgf_number"):
        assert field not in source, field


def test_opposition_context_is_gone_from_the_component():
    assert "contexto_oposicao" not in COMPONENT.read_text()


def test_component_shows_the_ept_notice_and_the_interventions_note():
    source = COMPONENT.read_text()
    assert "conflitosInteresse?.ept?.pendente" in source
    assert "atividades?.nota_intervencoes" in source


def test_conflitos_unknown_deputy_is_not_found(con):
    with pytest.raises(core.NotFound):
        deputies.conflitos_interesse(con, 99999)


# Routes


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_deputy_routes_serve_the_service_payloads(site_app, con):
    client = site_app.test_client()
    assert client.get("/api/deputados/1/detalhes").get_json() == deputies.detalhes(con, 1)
    assert client.get("/api/deputados/1/conflitos-interesse").get_json() == deputies.conflitos_interesse(con, 1)
    body = client.get(
        "/api/deputados/1/atividades?tipo_intervencao=Pedido&ordenacao_intervencoes=newest"
        "&legislatura=XVII&page=1&per_page=50"
    ).get_json()
    assert [i["tipo"] for i in body["intervencoes"]] == ["Pedido de esclarecimento"]


def test_deputy_routes_404_on_unknown_deputy_or_legislature(site_app):
    client = site_app.test_client()
    assert client.get("/api/deputados/99999/detalhes").status_code == 404
    assert client.get("/api/deputados/99999/conflitos-interesse").status_code == 404
    assert client.get("/api/deputados/1/atividades?legislatura=XL").status_code == 404


def test_deputy_routes_are_served_by_the_new_blueprint(app):
    endpoints = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert {endpoints[r].split(".")[0] for r in DEPUTY_ROUTES} == {"deputies"}


@pytest.mark.parametrize("path", ["app/routes/deputies.py", "app/services/deputies.py"])
def test_deputy_modules_have_no_sqlalchemy_or_old_database_import(path):
    tree = ast.parse((ROOT / path).read_text())
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert [n for n in names if n.split(".")[0] in {"sqlalchemy", "flask_sqlalchemy", "database"}] == []
