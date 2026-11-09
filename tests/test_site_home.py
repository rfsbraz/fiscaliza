"""#265: the home page composition strip and the state of the sources.

Seats and dates come from the synthetic release in tests/site_data.py (XVII extract date
2026-10-19). A copy of the file adds one temporary substitution inside the last 30 days:
person 150 (PS) suspends the mandate after 2026-09-30 and person 500, a substitute, takes a
seat as Efetivo Temporário from 2026-10-01.
"""

import shutil

import duckdb
import pytest

from app.services import home
from tests.site_data import build_site_data

DAY = "2026-10-19"


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"), sets=("deputies", "votes"))


@pytest.fixture(scope="module")
def plain(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def swapped(data_dir, tmp_path_factory):
    path = tmp_path_factory.mktemp("swap") / "swap.duckdb"
    shutil.copy((data_dir / "current.duckdb").resolve(), path)
    c = duckdb.connect(str(path))
    c.execute(
        "update mandates set end_date = date '2026-09-30' "
        "where legislature = 'XVII' and cadastro_id = 150 and situation = 'Efetivo'"
    )
    c.execute(
        "insert into mandates select legislature, cadastro_id, deputy_id, circle_id, 'Suspenso(Eleito)', false, "
        "date '2026-10-01', null from mandates where legislature = 'XVII' and cadastro_id = 150"
    )
    c.execute("update mandates set end_date = date '2026-09-30' where legislature = 'XVII' and cadastro_id = 500")
    c.execute(
        "insert into mandates select legislature, cadastro_id, deputy_id, circle_id, 'Efetivo Temporário', true, "
        "date '2026-10-01', null from mandates where legislature = 'XVII' and cadastro_id = 500 limit 1"
    )
    c.execute("insert into group_memberships values ('XVII', 500, 1, 'PS', date '2026-10-01', null, true)")
    yield c
    c.close()


def test_seats_by_group_with_the_government_groups_first(plain):
    comp = home.inicio(plain)["composicao"]
    assert comp["data"] == DAY
    assert comp["lugares"] == 230
    assert [(g["sigla"], g["deputados"], g["apoia_governo"]) for g in comp["grupos"]] == [
        ("PSD", 89, True),
        ("CDS-PP", 2, True),
        ("CH", 60, False),
        ("PS", 58, False),
        ("IL", 9, False),
        ("L", 6, False),
        ("PCP", 3, False),
        ("BE", 1, False),
        ("JPP", 1, False),
        ("PAN", 1, False),
    ]
    assert comp["governo"]["nome"] == "XXV Governo Constitucional"
    assert comp["governo"]["fonte"].startswith("https://www.portugal.gov.pt/")


def test_no_changes_in_the_last_30_days(plain):
    comp = home.inicio(plain)["composicao"]
    # 231 and 232 swapped on 2026-01-01, long before the window.
    assert comp["mudancas"] == {"desde": "2026-09-20", "ate": DAY, "itens": []}
    assert comp["substituicoes_temporarias"] == 0


def test_a_temporary_substitution_inside_the_window(swapped):
    comp = home.inicio(swapped)["composicao"]
    assert comp["lugares"] == 230
    assert comp["substituicoes_temporarias"] == 1
    assert comp["mudancas"]["itens"] == [
        {
            "data": "2026-10-01",
            "cadastro_id": 500,
            "nome": "Deputado 500",
            "grupo": "PS",
            "evento": "inicio",
            "situacao": "Efetivo Temporário",
        },
        {
            "data": "2026-09-30",
            "cadastro_id": 150,
            "nome": "Deputado 150",
            "grupo": "PS",
            "evento": "fim",
            "situacao": "Efetivo",
        },
    ]


def test_sources_have_a_date_per_dataset_and_the_known_gaps(plain):
    fontes = home.inicio(plain)["fontes"]
    assert fontes["tag"] == "data-2026-10-20"
    by_name = {c["nome"]: c["dados_ate"] for c in fontes["conjuntos"]}
    assert by_name == {
        "Votações em Plenário": "2026-05-04",
        "Iniciativas": "2025-11-01",
        "Intervenções": "2026-09-18",
        "Mandatos": DAY,
    }
    gaps = {g["conjunto"]: g for g in fontes["lacunas"]}
    # The synthetic release has declarations up to XVI (person 301), so XVII is missing.
    assert gaps["Declarações de interesses"]["tipo"] == "em_falta"
    assert "da XVII estão" in gaps["Declarações de interesses"]["texto"]
    # Interventions run past the last vote here, so they are not behind.
    assert "Intervenções" not in gaps


def test_interventions_behind_the_votes_are_a_coverage_gap(swapped):
    swapped.execute(
        "insert into votes (vote_id, legislature, date, body, result, unanimous) "
        "values (999, 'XVII', date '2026-10-15', 'plenary', 'Aprovado', true)"
    )
    try:
        gaps = {g["conjunto"]: g for g in home.inicio(swapped)["fontes"]["lacunas"]}
        assert gaps["Intervenções"]["tipo"] == "atraso"
        assert "18/09/2026" in gaps["Intervenções"]["texto"] and "15/10/2026" in gaps["Intervenções"]["texto"]
    finally:
        swapped.execute("delete from votes where vote_id = 999")
