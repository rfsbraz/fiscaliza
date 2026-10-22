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
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("deputies", "agenda"))


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
    assert s["intervencoes_parlamentares"] == 8
    assert s["total_mandatos"] == 2
    assert s["legislaturas_servidas"] == "XVI, XVII"
    assert s["nivel_experiencia"] == "Experiente"
    days = (date(2025, 6, 2) - date(2024, 3, 26)).days + (date.fromisoformat(EXTRACT) - date(2025, 6, 3)).days
    assert s["tempo_servico_anos"] == round(days / 365.25, 1)
    assert s["iniciativas_por_tipo"] == [
        {"codigo": "J", "descricao": "Projeto de Lei", "total": 7},
        {"codigo": "R", "descricao": "Projeto de Resolução", "total": 2},
        {"codigo": "A", "descricao": "Apreciação Parlamentar", "total": 1},
    ]
    assert s["evolucao_legislaturas"] == [
        {"legislatura": "XVII", "iniciativas": 9, "intervencoes": 3},
        {"legislatura": "XVI", "iniciativas": 1, "intervencoes": 5},
    ]


def test_no_career_total_rate_or_ranking(con):
    s = deputies.detalhes(con, 1)["estatisticas"]
    for key in (
        "iniciativas_propostas",
        "iniciativas_aprovadas",
        "taxa_aprovacao",
        "percentil_nacional",
        "media_partido_iniciativas",
        "media_partido_intervencoes",
        "iniciativas_legislatura",
        "intervencoes_legislatura",
    ):
        assert key not in s, key


def _row(codigo, descricao, aprovadas, parcialmente, rejeitadas, sem_votacao, taxa=None):
    return {
        "codigo": codigo,
        "descricao": descricao,
        "aprovadas": aprovadas,
        "aprovadas_parcialmente": parcialmente,
        "rejeitadas": rejeitadas,
        "votadas": aprovadas + rejeitadas,
        "taxa_aprovacao": taxa,
        "sem_votacao": sem_votacao,
    }


def test_approval_per_legislature_and_type_over_decided_initiatives(con):
    # XVII, projetos de lei: 1 passed its final global vote, 7 passed one point of two on the
    # same day, 10 failed the generality and passed a later final global vote, 9 failed the
    # generality. 3 was never voted and 4 only passed the generality: not decided, so outside
    # the rate. Projetos de resolução: 2 lost its deliberation vote, 8 passed a 'Votação final'.
    # The apreciação parlamentar (11) has no rate. Under 10 decided initiatives there is no rate.
    rows = deputies.detalhes(con, 1)["estatisticas"]["iniciativas_legislaturas"]
    assert [(r["legislatura"], r["aberta"]) for r in rows] == [("XVII", True), ("XVI", False)]
    assert rows[0]["aprovacao"] == [
        _row("J", "Projeto de Lei", 3, 1, 1, 2),
        _row("R", "Projeto de Resolução", 1, 0, 1, 0),
    ]
    assert rows[1]["aprovacao"] == [_row("J", "Projeto de Lei", 1, 0, 0, 0)]


def test_approval_rate_needs_ten_decided_initiatives(con):
    # PCP signs 30 to 41 as a group (7 passed, 5 failed); 222 and 223 also signed 42, which failed.
    (row,) = deputies.detalhes(con, 222)["estatisticas"]["iniciativas_legislaturas"]
    assert row["aprovacao"] == [_row("J", "Projeto de Lei", 7, 0, 6, 0, round(7 / 13 * 100, 1))]
    (row,) = deputies.detalhes(con, 224)["estatisticas"]["iniciativas_legislaturas"]
    assert row["aprovacao"][0]["taxa_aprovacao"] == round(7 / 12 * 100, 1)


def test_a_committee_vote_does_not_count_as_approval(con):
    (row,) = deputies.detalhes(con, 2)["estatisticas"]["iniciativas_legislaturas"]
    assert row["aprovacao"] == [_row("J", "Projeto de Lei", 0, 0, 0, 1)]


def test_initiatives_split_by_how_they_were_signed(con):
    # Person 1 signs alone for PSD (89 seats): restricted list. 4 is signed with a CH deputy.
    rows = deputies.detalhes(con, 1)["estatisticas"]["iniciativas_legislaturas"]
    assert [r["assinatura"] for r in rows] == [
        {"grupo_parlamentar": 0, "subscricao_restrita": 7, "outros_grupos": 1},
        {"grupo_parlamentar": 0, "subscricao_restrita": 1, "outros_grupos": 0},
    ]
    # The three PCP deputies sign 12 as a whole group; 42 lists two of the three.
    (row,) = deputies.detalhes(con, 222)["estatisticas"]["iniciativas_legislaturas"]
    assert row["assinatura"] == {"grupo_parlamentar": 12, "subscricao_restrita": 1, "outros_grupos": 0}
    # A group with one seat signs as a whole group.
    (row,) = deputies.detalhes(con, 227)["estatisticas"]["iniciativas_legislaturas"]
    assert row["assinatura"] == {"grupo_parlamentar": 1, "subscricao_restrita": 0, "outros_grupos": 0}
    assert row["aprovacao"] == [_row("J", "Projeto de Lei", 0, 0, 0, 1)]


def test_comparison_within_the_group_per_seat_year(con):
    c = deputies.detalhes(con, 1)["estatisticas"]["comparacao"]
    # XVII, PSD: 89 deputies seated the whole legislature (503 days to the extract date).
    # Restricted lists: person 1 signed 7 and person 2 one.
    assert c["iniciativas_subscricao_restrita"] == {
        "legislatura": "XVII",
        "grupo": "PSD",
        "deputado_por_ano": round(7 * 365.25 / 503, 2),
        "media_grupo_por_ano": round(8 * 365.25 / 503 / 89, 2),
        "pares": 88,
        "nota": None,
    }
    # Interventions only for a closed legislature: XVI, PS, 27 deputies seated all 433 days.
    assert c["intervencoes"] == {
        "legislatura": "XVI",
        "grupo": "PS",
        "deputado_por_ano": round(5 * 365.25 / 433, 2),
        "media_grupo_por_ano": round(5 * 365.25 / 433 / 27, 2),
        "pares": 26,
        "nota": None,
    }


def test_no_comparison_for_a_small_group(con):
    c = deputies.detalhes(con, 222)["estatisticas"]["comparacao"]["iniciativas_subscricao_restrita"]
    assert c["pares"] == 2 and c["media_grupo_por_ano"] is None
    assert c["nota"] == "Grupo demasiado pequeno para comparação"


def test_no_comparison_for_a_short_mandate(con):
    # 231 sat 211 of XVII's 503 days, under half.
    c = deputies.detalhes(con, 231)["estatisticas"]["comparacao"]
    assert c["iniciativas_subscricao_restrita"]["media_grupo_por_ano"] is None
    assert c["iniciativas_subscricao_restrita"]["nota"] == "Mandato curto nesta legislatura; sem comparação"
    # 231 never sat in a closed legislature, so there is nothing to compare interventions with.
    assert c["intervencoes"]["legislatura"] is None and c["intervencoes"]["media_grupo_por_ano"] is None
    assert c["intervencoes"]["nota"] == "Sem legislatura concluída para comparar intervenções"


def test_dropped_and_unavailable_fields(con):
    s = deputies.detalhes(con, 1)["estatisticas"]
    assert "contexto_oposicao" not in s  # F09
    assert "taxa_assiduidade" not in s  # replaced by estatisticas.assiduidade (S11)


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


def test_intervention_comparison_only_for_a_closed_legislature(con):
    # XVI: person 1 has all 5 interventions; 27 PS deputies seated all 433 days.
    a = deputies.atividades(con, 1, "XVI")
    assert "medias_intervencoes" not in a
    assert a["comparacao_intervencoes"] == {
        "legislatura": "XVI",
        "grupo": "PS",
        "deputado_por_ano": round(5 * 365.25 / 433, 2),
        "media_grupo_por_ano": round(5 * 365.25 / 433 / 27, 2),
        "pares": 26,
        "nota": None,
    }
    open_leg = deputies.atividades(con, 1)["comparacao_intervencoes"]
    assert open_leg["media_grupo_por_ano"] is None
    assert open_leg["nota"] == "A XVII Legislatura ainda está em curso; sem comparação de intervenções"
    assert deputies.atividades(con, 300, "XVII")["comparacao_intervencoes"] is None


def test_open_legislature_says_the_interventions_are_incomplete(con):
    note = deputies.atividades(con, 1)["nota_intervencoes"]
    # 4 from the deputy activity and 4 from the agenda page (tests/site_agenda.py).
    assert "XVII" in note and "8 intervenções" in note
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
    a = deputies.atividades(con, 1)
    found = {i["id"]: i for i in a["iniciativas"]}
    assert list(found) == [4, 3, 11, 2, 10, 9, 8, 7, 1]
    assert (found[1]["estado"], found[1]["resultado"], found[1]["aprovada"]) == ("Aprovado", "Aprovado", True)
    assert (found[2]["estado"], found[2]["aprovada"]) == ("Rejeitado", False)
    assert found[3]["estado"] is None and found[3]["resultado"] is None
    assert found[4]["estado"] is None  # passed the generality only
    assert (found[7]["estado"], found[7]["aprovada_parcialmente"]) == ("Aprovado", True)
    assert found[1]["aprovada_parcialmente"] is False
    assert (found[8]["estado"], found[9]["estado"], found[10]["estado"]) == ("Aprovado", "Rejeitado", "Aprovado")
    assert found[4]["autores"] == ["Deputado 1", "Deputado 90"] and found[4]["subscricao"] == "outros_grupos"
    assert found[1]["autores"] == ["Deputado 1"] and found[1]["subscricao"] == "subscricao_restrita"
    assert found[1]["subscritores"] == 1 and found[4]["subscritores"] == 2
    assert found[11]["subscricao"] is None  # only projetos de lei, resolução and deliberação
    assert "is_cross_party" not in found[1]
    assert a["assinatura"] == {"grupo_parlamentar": 0, "subscricao_restrita": 7, "outros_grupos": 1}
    assert a["aprovacao"] == [
        _row("J", "Projeto de Lei", 3, 1, 1, 2),
        _row("R", "Projeto de Resolução", 1, 0, 1, 0),
    ]
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
    assert c["professional_activities"] == [
        {
            "function_type": "Consultor",
            "entity_name": "Empresa Exemplo",
            "location": "Lisboa",
            "start_date": "2019-01-01",
            "end_date": "2021-06-30",
        },
        {
            "function_type": "Deputado",
            "entity_name": "Assembleia da República",
            "location": "Lisboa",
            "start_date": "2022-03-29",
            "end_date": None,
        },
        {
            "function_type": "Consultor",
            "entity_name": "Empresa Exemplo",
            "location": "Lisboa",
            "start_date": "2021-07-01",
            "end_date": None,
        },
    ]
    assert c["shareholdings"] == [{"entity_name": "Sociedade Exemplo", "share_percentage": "10", "location": "Porto"}]
    assert c["is_exclusive"] is False
    assert (c["declara_outras_atividades"], c["declara_participacoes"]) == (True, True)
    assert "has_conflict_potential" not in c


def test_repeated_items_are_shown_once_and_other_periods_keep_their_dates(con):
    # Item 6 repeats item 1 as published; item 5 is the same post for a later period. Without the
    # dates the two periods looked like duplicate rows.
    activities = deputies.conflitos_interesse(con, 1)["professional_activities"]
    consultor = [(a["start_date"], a["end_date"]) for a in activities if a["function_type"] == "Consultor"]
    assert consultor == [("2019-01-01", "2021-06-30"), ("2021-07-01", None)]


def test_a_declaration_without_an_entity_keeps_the_text_in_one_field(con):
    [activity] = deputies.conflitos_interesse(con, 2)["professional_activities"]
    assert activity["function_type"] == "Deputada à Assembleia da República"
    assert activity["entity_name"] is None
    assert activity["start_date"] == "2011"


def test_no_sector_or_legislation_figures_without_a_source(con):
    # The release has no sector classification and no legislation matching, so neither the
    # payload nor the page claims any.
    c = deputies.conflitos_interesse(con, 1)
    assert "regulated_sector_count" not in c and "total_sectors" not in c
    source = COMPONENT.read_text()
    for gone in (
        "SectorHeatmap",
        "SectorOverlapSummary",
        "legislationCount",
        "noLegislation",
        "regulated_sector_count",
    ):
        assert gone not in source, gone


def test_interest_table_shows_only_the_columns_with_data():
    source = COMPONENT.read_text()
    assert "activity.entity_name || activity.function_type" not in source
    assert "<InterestTable" in source
    table = (ROOT / "frontend" / "src" / "components" / "deputy" / "InterestTable.jsx").read_text()
    for column in ("Cargo ou função", "Entidade", "Local", "Período", "Participação"):
        assert column in table, column
    # A column is drawn only when at least one row has a value for it.
    assert "columns.filter((column) => rows.some((row) => hasValue(row[column.key])))" in table


def test_the_mandate_itself_is_not_another_activity_and_blank_exclusivity_stays_blank(con):
    c = deputies.conflitos_interesse(con, 2)
    assert (c["declara_outras_atividades"], c["declara_participacoes"]) == (False, False)
    assert c["is_exclusive"] is None


def test_coverage_of_the_ar_declarations(con):
    # The synthetic release has AR declarations for XV and XVI but only XVI as a legislature; of
    # the 230 people seated in XVI only 301 has a declaration.
    for cad in (1, 300):
        assert deputies.conflitos_interesse(con, cad)["cobertura"] == {
            "de": "XVI",
            "ate": "XVI",
            "com_declaracao": 1,
            "total": 230,
        }


def test_no_declaration_in_the_open_data_is_not_a_missing_declaration(con):
    # #106: 300 sat only in XVI, has no AR declaration and the EpT note covers XVI. The page gets
    # what it needs to say the open data lacks it, never that it was not submitted.
    c = deputies.conflitos_interesse(con, 300)
    assert c["tem_declaracao"] is False
    assert c["sem_declaracao"] == {
        "legislatura": "XVI",
        "antes_da_cobertura": False,
        "lei_52_2019": True,
        "url_parlamento": "https://www.parlamento.pt/DeputadoGP/Paginas/RegistoInteressesInfo.aspx?bid=300",
        "url_ept": "https://entidadetransparencia.pt/",
    }
    assert "sem_declaracao" not in deputies.conflitos_interesse(con, 1)


@pytest.mark.parametrize(
    ("start", "before", "law"),
    [
        (date(2005, 3, 10), True, False),  # X: before the open data's first declarations (XI)
        (date(2009, 10, 15), False, False),  # XI: covered, older regime
        (date(2015, 10, 23), False, False),  # XIII: ended before Lei 52/2019 came into force
        (date(2019, 10, 25), False, True),  # XIV: first day of the law (art. 26.º)
        (date(2022, 3, 29), False, True),  # XV
    ],
)
def test_missing_declaration_note_by_legislature(start, before, law):
    note = deputies.missing_declaration(7, "L", start, date(2009, 10, 15))
    assert (note["antes_da_cobertura"], note["lei_52_2019"]) == (before, law)
    assert note["url_parlamento"].endswith("?bid=7")


def test_component_never_says_a_declaration_was_not_submitted():
    source = COMPONENT.read_text()
    card = (ROOT / "frontend" / "src" / "components" / "deputy" / "InterestStatusCard.jsx").read_text()
    assert "hasDeclaration: false" not in source
    for text in (source, card):
        assert "30 dias" not in text
    assert "Isso não significa que não tenha sido entregue" in source
    assert "não cobrem declarações de interesses" in source
    assert "60 dias" in source and "art. 13.º, n.º 1" in source
    assert "conflitosInteresse.sem_declaracao.lei_52_2019" in source
    # The tab covers mandates from before the law too, so its subtitle doesn't cite it.
    assert "conforme Lei n.º 52/2019" not in source


def test_component_uses_the_neutral_interest_labels():
    source = COMPONENT.read_text()
    assert "has_conflict_potential" not in source
    assert "Conflitos de Interesse" not in source
    assert "label: 'Registo de Interesses'" in source
    assert "conflitosInteresse.declara_outras_atividades" in source
    assert "conflitosInteresse?.cobertura" in source
    assert "\u2014" not in source and "—" not in source
    badge = (ROOT / "frontend" / "src" / "components" / "deputy" / "InterestStatusCard.jsx").read_text()
    for copy in (
        "Declara outras atividades ou participações",
        "Não declara outras atividades nem participações",
        "Não indicado na declaração",
    ):
        assert copy in badge or copy in source, copy


def test_component_reads_the_new_initiative_keys():
    source = COMPONENT.read_text()
    for key in ("percentil_nacional", "iniciativas_propostas", "media_partido_intervencoes", "is_cross_party"):
        assert key not in source, key
    for key in ("iniciativas_legislaturas", "comparacao_intervencoes", "atividades.assinatura"):
        assert key in source, key


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


# Evolution chart


def test_evolution_bars_are_scaled_to_their_values():
    # A percentage height inside a column with no height of its own resolves to auto, so every
    # bar fell back to the same minimum. The bars get a pixel height out of a fixed track.
    source = COMPONENT.read_text()
    assert "height: `${Math.max(height, 8)}%`" not in source
    assert "const EVOLUTION_TRACK_PX = " in source
    assert "Math.round((total / maxValue) * EVOLUTION_TRACK_PX)" in source
    assert "height: `${barHeight}px`" in source


def test_coverage_counts_people_with_an_effective_mandate_once():
    # #106 / #113: the base is people with an effective mandate in any legislature with AR
    # declarations, each counted once (793 with 149 declared on the pin), not person-legislature
    # pairs (1,425 and 297). Suplentes who never sat are not in the base.
    import duckdb

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
