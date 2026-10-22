"""Written questions to the Government (#114): a page per legislature with the answer rate and
the median days to answer, per recipient.

Values are checked against the questions set in tests/site_questions.py. A pergunta is a
written question to the central administration (``question_type='Pergunta'``,
``recipient_category='AC'``). Withdrawn and returned ones are owed no answer, so they are
counted apart and left out of the rate and the median. A question to two recipients counts once
for each recipient, and once in the legislature totals.
"""

from pathlib import Path

import duckdb
import pytest

from app.services import core, questions
from tests.site_data import build_site_data

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "frontend" / "src" / "components" / "PerguntasPage.jsx"
APP = ROOT / "frontend" / "src" / "App.jsx"
NAVIGATION = ROOT / "frontend" / "src" / "components" / "Navigation.jsx"


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    data_dir = build_site_data(tmp_path_factory.mktemp("questions"), sets=("questions",))
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def empty_con(tmp_path_factory):
    data_dir = build_site_data(tmp_path_factory.mktemp("no-questions"), sets=("deputies",))
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def _row(destinatario, perguntas, respondidas, taxa, mediana, sem_data=0, retiradas=0, devolvidas=0):
    return {
        "destinatario": destinatario,
        "perguntas": perguntas,
        "respondidas": respondidas,
        "taxa_resposta": taxa,
        "mediana_dias": mediana,
        "respondidas_sem_data": sem_data,
        "retiradas": retiradas,
        "devolvidas": devolvidas,
    }


def _totals(*args, **kwargs):
    row = _row(None, *args, **kwargs)
    row.pop("destinatario")
    return row


def test_open_legislature_per_recipient_and_marked_provisional(con):
    page = questions.perguntas_legislatura(con, "XVII")
    assert (page["legislatura"], page["provisoria"]) == ("XVII", True)
    assert (page["data_inicio"], page["data_fim"]) == ("2025-06-03", None)
    # 7001 (20 days), 7002 (40 days), 7003 and 7004 to Saúde; 7004 (30 days) to Finanças, where
    # 7005 was withdrawn and 7007 returned.
    assert page["destinatarios"] == [
        _row("Ministra da Saúde", 4, 2, 50.0, 30),
        _row("Ministro das Finanças", 1, 1, 100.0, 30, retiradas=1, devolvidas=1),
    ]
    # 7001 to 7004, each once; 7004 is answered by one of its two recipients.
    assert page["totais"] == _totals(4, 3, 75.0, 30, retiradas=1, devolvidas=1)


def test_closed_legislature_and_an_answer_without_a_date(con):
    page = questions.perguntas_legislatura(con, "XVI")
    assert page["provisoria"] is False
    # 6002's recipient is spaced differently and still counts for Ministro das Finanças. 6003 was
    # answered but has no answer date: it counts as answered and stays out of the median.
    assert page["destinatarios"] == [
        _row("Ministro das Finanças", 2, 2, 100.0, 10, sem_data=1),
        _row("Ministra da Saúde", 1, 1, 100.0, 40),
    ]
    assert page["totais"]["mediana_dias"] == 25
    assert page["totais"]["respondidas_sem_data"] == 1


def test_requerimentos_are_not_perguntas(con):
    # 7006 is a requerimento to Finanças, unanswered: it would lower the rate if counted.
    page = questions.perguntas_legislatura(con, "XVII")
    financas = next(r for r in page["destinatarios"] if r["destinatario"] == "Ministro das Finanças")
    assert financas["perguntas"] == 1


def test_index_lists_the_legislatures_with_perguntas_newest_first(con):
    assert questions.perguntas(con) == {
        "legislaturas": [
            {
                "legislatura": "XVII",
                "provisoria": True,
                "perguntas": 4,
                "respondidas": 3,
                "taxa_resposta": 75.0,
                "mediana_dias": 30,
            },
            {
                "legislatura": "XVI",
                "provisoria": False,
                "perguntas": 3,
                "respondidas": 3,
                "taxa_resposta": 100.0,
                "mediana_dias": 25,
            },
        ]
    }


def test_unknown_legislature_or_one_without_perguntas_is_not_found(con, empty_con):
    with pytest.raises(core.NotFound):
        questions.perguntas_legislatura(con, "XL")
    with pytest.raises(core.NotFound):
        questions.perguntas_legislatura(empty_con, "XVII")
    assert questions.perguntas(empty_con) == {"legislaturas": []}


def test_page_marks_the_open_legislature_provisional_and_has_no_deadline():
    source = PAGE.read_text()
    for copy in (
        "Perguntas ao Governo",
        "Taxa de resposta",
        "Mediana de dias até à resposta",
        "Provisório",
        "toLocaleString('pt-PT'",
    ):
        assert copy in source, copy
    lowered = source.lower()
    assert "prazo" not in lowered and "dentro do prazo" not in lowered
    assert "\u2014" not in source


def test_page_has_a_route_and_a_menu_entry():
    assert '<Route path="/perguntas" element={<PerguntasPage />} />' in APP.read_text()
    assert '<Route path="/perguntas/:legislatura" element={<PerguntasPage />} />' in APP.read_text()
    assert "path: '/perguntas'" in NAVIGATION.read_text()
