"""#263: which plenary votes count as decisions, on a small synthetic day.

The rule: final votes (votação final global, votação final, votação global) of any initiative,
and the vote on the generality of a proposta de lei (the Orçamento do Estado is one). An
initiative decided in a final vote on the same day shows once, as that final vote.
"""

import duckdb
import pytest

from app.data import repository
from app.services import decisions

DAY = "2026-10-28"


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute(
        "create table votes (vote_id bigint, legislature varchar, date date, body varchar, result varchar, "
        "unanimous boolean, description varchar)"
    )
    c.execute(
        "create table initiative_votes (vote_id bigint, initiative_id bigint, initiative_legislature varchar, "
        "body varchar, phase varchar)"
    )
    c.execute(
        "create table initiatives (legislature varchar, initiative_id bigint, number integer, type_code varchar, "
        "type varchar, title varchar, author_kind varchar)"
    )
    kinds = {"P": "Proposta de Lei", "J": "Projeto de Lei", "R": "Projeto de Resolução"}
    for ini, code, author in [
        (1, "P", "Governo"),  # OE: generality only
        (2, "P", "Governo"),  # generality and final on the same day
        (3, "J", "Grupos Parlamentares"),  # generality, specialty and final
        (4, "J", "Grupos Parlamentares"),  # generality only: not a decision
        (5, "R", "Grupos Parlamentares"),  # votação final
        (6, "R", "PAR"),  # deliberação
        (7, "J", "Grupos Parlamentares"),  # procedural request only
        (8, "S", "Governo"),  # votação global
    ]:
        c.execute(
            "insert into initiatives values ('XVII', ?, ?, ?, ?, ?, ?)",
            [ini, ini * 10, code, kinds.get(code, "Proposta de Resolução"), f"Iniciativa {ini}", author],
        )
    links = [
        (10, 1, "Votação na generalidade"),
        (20, 2, "Votação na generalidade"),
        (21, 2, "Votação final global"),
        (30, 3, "Votação na generalidade"),
        (31, 3, "Votação na especialidade"),
        (32, 3, "Votação final global"),
        (32, 3, "Votação final global"),  # the same link listed twice
        (40, 4, "Votação na generalidade"),
        (50, 5, "Votação final"),
        (50, 5, "Votação final global"),  # the same initiative under a second final phase
        (60, 6, "Votação Deliberação"),
        (70, 7, "Requerimento dispensa redação final"),
        (80, 8, "Votação global"),
    ]
    for vote, ini, phase in links:
        c.execute("insert into initiative_votes values (?, ?, 'XVII', 'plenary', ?)", [vote, ini, phase])
    for vote in sorted({v for v, _, _ in links}) + [90]:  # 90 has no initiative
        c.execute("insert into votes values (?, 'XVII', ?, 'plenary', 'Aprovado', false, null)", [vote, DAY])
    # An older day and a committee vote never show
    c.execute("insert into votes values (99, 'XVII', '2026-10-01', 'plenary', 'Aprovado', false, null)")
    c.execute("insert into initiative_votes values (99, 5, 'XVII', 'plenary', 'Votação final')")
    c.execute("insert into votes values (98, 'XVII', ?, 'Comissão de Saúde', 'Aprovado', false, null)", [DAY])
    c.execute("insert into initiative_votes values (98, 5, 'XVII', 'Comissão de Saúde', 'Votação final')")
    yield c
    c.close()


def test_the_latest_day_is_the_last_plenary_vote_day(con):
    assert str(repository.last_plenary_vote_day(con)) == DAY


def test_finals_and_the_generality_of_propostas_de_lei(con):
    rows = repository.plenary_decisions(con, DAY)
    assert [r["vote_id"] for r in rows] == [10, 21, 32, 50, 80]


def test_one_decision_per_initiative_and_no_duplicate_links(con):
    rows = {r["vote_id"]: r for r in repository.plenary_decisions(con, DAY)}
    assert [i["initiative_id"] for i in rows[32]["initiatives"]] == [3]
    assert [i["initiative_id"] for i in rows[50]["initiatives"]] == [5]
    assert 20 not in rows  # the final vote 21 decided initiative 2 the same day


def test_the_service_names_the_kind_and_the_day(con):
    payload = decisions.latest_decisions(con)
    assert payload["data"] == DAY
    kinds = {d["vote_id"]: d["tipo"] for d in payload["decisoes"]}
    assert kinds == {10: "generalidade", 21: "final", 32: "final", 50: "final", 80: "final"}
    oe = next(d for d in payload["decisoes"] if d["vote_id"] == 10)
    assert oe["iniciativas"] == [
        {
            "id": 1,
            "legislatura": "XVII",
            "tipo": "Proposta de Lei",
            "numero": 10,
            "titulo": "Iniciativa 1",
            "autoria": "Governo",
        }
    ]


def test_no_plenary_votes_means_no_day():
    c = duckdb.connect()
    c.execute("create table votes (vote_id bigint, date date, body varchar)")
    assert repository.last_plenary_vote_day(c) is None
    assert decisions.latest_decisions(c) == {"data": None, "decisoes": []}
