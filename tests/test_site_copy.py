"""Site copy in pt-PT and pt-PT number formatting (#112)."""

import re
from pathlib import Path

import pytest

from app.services import core

SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"
COMPONENTS = SRC / "components"


def _sources():
    return sorted(p for p in COMPONENTS.rglob("*.jsx"))


def test_first_assembly_is_called_assembleia_constituinte():
    assert core.legislature_designation("Constituinte") == "Assembleia Constituinte"
    assert core.legislature_designation("XVII") == "XVII Legislatura"
    assert core.legislature_designation("I-A") == "I-A Legislatura"


@pytest.mark.parametrize(
    "wrong",
    [
        "Carregando",
        "Mostrando",
        "registrado",
        "registro de",
        "colaboração cross-party",
        "não informada",
        ">Status:<",
        "Link Oficial",
        "ª Leg.",
        "distritos eleitorais",
        "eleitos ·",
        "</span> eleitos",
    ],
)
def test_no_pt_br_or_wrong_label_in_the_components(wrong):
    hits = [p.name for p in _sources() if wrong in p.read_text()]
    assert hits == []


def test_seated_line_says_who_had_a_seat_not_who_was_elected():
    home = (COMPONENTS / "Dashboard.jsx").read_text()
    assert "tiveram lugar nesta legislatura" in home
    deputados = (COMPONENTS / "DeputadosPage.jsx").read_text()
    assert "em exercício na data dos dados · " in deputados
    assert "tiveram lugar na legislatura atual" in deputados


def test_seated_count_is_dated_to_the_data_not_today():
    # The 230 is the seated count on the data date, not on the day the page is read.
    home = (COMPONENTS / "Dashboard.jsx").read_text()
    assert 'label="Em exercício na data dos dados"' in home
    for name in ("Dashboard.jsx", "DeputadosPage.jsx"):
        assert "em exercício hoje" not in (COMPONENTS / name).read_text().lower()


def test_counts_with_a_noun_agree_in_number():
    assert "{dados.mandatos_ativos} mandatos ativos" not in (COMPONENTS / "PartidoDetalhes.jsx").read_text()
    assert "{partidos.length} partidos componentes" not in (COMPONENTS / "ColigacaoDetalhes.jsx").read_text()
    assert "{deputado.career_info.total_mandates} mandatos" not in (COMPONENTS / "DeputadosPage.jsx").read_text()
    assert "{dados.mandatos_ativos} ativos" not in (COMPONENTS / "PartidoDetalhes.jsx").read_text()
    deputy = (COMPONENTS / "DeputadoDetalhes.jsx").read_text()
    assert "{deputado.estatisticas.total_mandatos === 1 ? 'mandato' : 'mandatos'}" in deputy


def test_numbers_are_formatted_with_the_pt_pt_helpers():
    # toFixed prints a decimal point; the helpers in utils/format.js print pt-PT (100,0%).
    hits = [
        f"{p.name}:{i}"
        for p in _sources()
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if ".toFixed(" in line
    ]
    assert hits == []
    helper = (SRC / "utils" / "format.js").read_text()
    assert "'pt-PT'" in helper


def test_service_time_and_agenda_figures_go_through_the_helpers():
    deputy = (COMPONENTS / "DeputadoDetalhes.jsx").read_text()
    assert not re.search(r"\{deputado\.estatisticas\.tempo_servico_anos\}", deputy)
    agenda = (COMPONENTS / "AgendaPage.jsx").read_text()
    assert "${estatisticas.estatisticas.votacoes.taxa_aprovacao}%" not in agenda


@pytest.mark.parametrize(
    ("component", "wrong"),
    [
        ("DeputadoDetalhes.jsx", "{latest.legislatura} Legislatura"),
        ("deputy/InitiativeRecord.jsx", "{row.legislatura} Legislatura"),
        ("deputy/InitiativeRecord.jsx", "${comparacao.legislatura} Legislatura"),
        ("deputy/AttendancePanel.jsx", "{assiduidade.legislatura} Legislatura"),
        ("deputy/AttendancePanel.jsx", "{leg.legislatura} Legislatura"),
        ("PartidosPage.jsx", "${numero} Legislatura"),
        ("Dashboard.jsx", "${legislatura.numero} Legislatura"),
    ],
)
def test_legislature_names_go_through_legislature_name(component, wrong):
    # The first assembly is "Assembleia Constituinte", not "Constituinte Legislatura" (#108).
    assert wrong not in (COMPONENTS / component).read_text()
