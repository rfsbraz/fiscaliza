"""S7: the party page's deputies list and demographics (F22, F23) on the DuckDB data layer.

Values are checked against the synthetic release in tests/site_data.py. In XVII, PSD holds
seats 1 to 89 (1 to 50 also sat in XVI) and PS holds 150 to 206 and 232. Person 1 sat for PS
in XVI and for PSD in XVII; person 231 sat for PS in XVII and resigned.
"""

import duckdb
import pytest

from app.services import parties
from tests.site_data import KNOWN_SPLIT, build_site_data


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("deputies", "agenda"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


# Deputies list (F22)


def test_lists_everyone_who_held_a_seat_for_the_group_once(con):
    body = parties.partido_deputados(con, "PS")
    ids = [d["id_cadastro"] for d in body["deputados"]]
    # 27 in XVI, 57 + 231 + 232 in XVII.
    assert len(ids) == len(set(ids)) == body["total"] == 86
    assert body["mandatos_ativos"] == 58
    assert body["partido"] == {"sigla": "PS", "nome": "Grupo PS"}


def test_seated_deputies_come_first_and_others_show_their_last_legislature_for_the_group(con):
    deputies = parties.partido_deputados(con, "PS")["deputados"]
    by_id = {d["id_cadastro"]: d for d in deputies}
    assert all(d["mandato_ativo"] for d in deputies[:58])
    assert not any(d["mandato_ativo"] for d in deputies[58:])
    # Person 1 is seated today, but for PSD.
    assert by_id[1]["mandato_ativo"] is False and by_id[1]["ultima_legislatura"] == "XVI"
    assert by_id[231]["mandato_ativo"] is False and by_id[231]["ultima_legislatura"] == "XVII"
    assert by_id[232]["mandato_ativo"] is True and by_id[232]["ultima_legislatura"] == "XVII"
    assert by_id[232]["id"] == 232 and by_id[232]["nome"] == "Deputado 232"


def test_history_counts_legislatures_and_circles(con):
    historico = parties.partido_deputados(con, "PS")["historico"]
    assert historico["total_legislaturas"] == 2
    assert historico["periodo_atividade"] == "desde 2024"
    assert historico["total_circulos"] == 22


def test_legislatura_limits_the_list_and_the_demographics(con):
    body = parties.partido_deputados(con, "PS", "XVI")
    assert body["total"] == 27 and body["legislatura"] == "XVI"
    assert sum(body["demografia"]["genero"].values()) == 27


def test_coalition_of_the_group_in_the_legislature(con):
    # PSD ran on both AD lists in XVII: the link goes to the national one (#111).
    assert parties.partido_deputados(con, "PSD")["coligacao"] == {
        "id": "ad-2024",
        "sigla": "AD",
        "nome": "Coligação AD",
    }
    assert parties.partido_deputados(con, "PS")["coligacao"] is None
    assert parties.partido_deputados(con, "PS", "XVI")["coligacao"] == {
        "id": "FRS",
        "sigla": "FRS",
        "nome": "Coligação FRS",
    }


def test_unknown_group_or_legislature_is_not_found(con):
    with pytest.raises(parties.NotFound):
        parties.partido_deputados(con, "XYZ")
    with pytest.raises(parties.NotFound):
        parties.partido_deputados(con, "PS", "XL")


# Demographics (F23)


def test_demographics_cover_the_groups_seated_deputies(con):
    demo = parties.partido_deputados(con, "PSD")["demografia"]
    assert demo["genero"] == {"Feminino": 45, "Masculino": 44}
    assert demo["renovacao"]["novos_deputados"] == 39
    assert demo["renovacao"]["veteranos"] == 50
    assert demo["renovacao"]["percentual_renovacao"] == 43.8
    assert demo["experiencia_politica"]["mandatos_anteriores"] == {"1": 39, "2": 50}
    assert demo["experiencia_politica"]["categorias"] == {"Primeiro Mandato": 39, "Experiente (2-3 mandatos)": 50}


def test_ages_are_on_the_reference_day_and_skip_people_without_a_birth_date(con):
    idades = parties.partido_deputados(con, "PSD")["demografia"]["idades"]
    # 10, 20, ..., 80 have no birth date.
    assert idades["total_com_idade"] == 81
    assert sum(idades["cohorts_geracionais"].values()) == 81
    assert idades["oldest_deputy"]["id_cadastro"] == 1 and idades["oldest_deputy"]["idade"] == 85
    assert idades["youngest_deputy"]["id_cadastro"] == 49 and idades["youngest_deputy"]["idade"] == 37
    assert (idades["min"], idades["max"]) == (37, 85)


def test_demographic_totals_for_xvii_add_up_to_230(con):
    totals = {"genero": 0, "regional": 0, "renovacao": 0, "mandatos": 0, "idade": 0}
    for group in KNOWN_SPLIT:
        demo = parties.partido_deputados(con, group)["demografia"]
        totals["genero"] += sum(demo["genero"].values())
        totals["regional"] += sum(demo["geografia"]["regional"].values())
        totals["renovacao"] += demo["renovacao"]["novos_deputados"] + demo["renovacao"]["veteranos"]
        totals["mandatos"] += sum(demo["experiencia_politica"]["mandatos_anteriores"].values())
        totals["idade"] += demo["idades"]["total_com_idade"] + demo["idades"]["sem_idade"]
    assert totals == dict.fromkeys(totals, 230)


def test_no_education_or_urban_rural_split_without_a_source(con):
    demo = parties.partido_deputados(con, "PSD")["demografia"]
    assert "educacao" not in demo
    assert "urbano_rural" not in demo["geografia"]


@pytest.mark.parametrize(
    ("circle", "region"),
    [
        ("Lisboa", "Lisboa e Vale do Tejo"),
        ("Bragança", "Norte"),
        ("Castelo Branco", "Centro"),
        ("Portalegre", "Alentejo"),
        ("Faro", "Algarve"),
        ("Madeira", "Madeira"),
        ("Fora da Europa", "Emigração"),
        ("Círculo 3", "Outros"),
    ],
)
def test_region_of_circle(circle, region):
    assert parties.region(circle) == region


@pytest.mark.parametrize(
    ("profession", "category"),
    [
        ("Advogada", "Direito"),
        ("Professor Universitário", "Educação"),
        ("Médica", "Saúde"),
        ("Engenheiro Civil", "Engenharia/Técnico"),
        ("Gestora", "Economia/Gestão"),
        ("Autarca", "Política"),
        ("Agricultor", "Outras"),
    ],
)
def test_profession_category(profession, category):
    assert parties.profession_category(profession) == category


# Route


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_route_serves_the_service_payload_and_404s(site_app, con):
    client = site_app.test_client()
    response = client.get("/api/partidos/CDS-PP/deputados")
    assert response.status_code == 200
    assert response.get_json() == parties.partido_deputados(con, "CDS-PP")
    assert client.get("/api/partidos/XYZ/deputados").status_code == 404


def test_route_is_served_by_the_parties_blueprint(app):
    endpoints = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert endpoints["/api/partidos/<path:partido_sigla>/deputados"].startswith("parties.")
