"""Deputy page rules checked on a real parlamento-aberto release.

Skipped unless FISCALIZA_RELEASE_DIR points at a release folder (manifest.json and the Parquet
files, for example a local `release build` of parlamento-aberto). The figures are pinned on
data-2026-10-20, so the tests skip on any other tag. Only counts and ids, no names.
"""

import os
from pathlib import Path

import duckdb
import pytest

from app.data import repository
from app.services import deputies
from fiscaliza_data import sync

RELEASE = os.environ.get("FISCALIZA_RELEASE_DIR")
TAG = "data-2026-10-20"
DEPUTY = 4197  # a deputy seated from XI to XVII for a three to four seat group

pytestmark = pytest.mark.skipif(not RELEASE, reason="FISCALIZA_RELEASE_DIR is not set")


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    result = sync.sync(tmp_path_factory.mktemp("release") / "data", from_dir=Path(RELEASE))
    if result.tag != TAG:
        pytest.skip(f"figures are pinned on {TAG}, not {result.tag}")
    c = duckdb.connect(str(result.path), read_only=True)
    yield c
    c.close()


def _deputy_projetos(con, where="true"):
    return con.execute(
        f"""
        select i.legislature,
               count(*) filter (o.result = 'Aprovado') as approved,
               count(*) filter (o.result = 'Rejeitado') as rejected
        from initiatives i
        join (select distinct legislature, initiative_id from deputy_initiatives) d
          on d.legislature = i.legislature and d.initiative_id = i.initiative_id
        left join initiative_outcome o on o.legislature = i.legislature and o.initiative_id = i.initiative_id
        where i.type_code in ('J', 'R', 'D') and {where}
        group by i.legislature
        """  # noqa: S608 - fixed test filters
    ).fetchall()


def test_approval_over_decided_projetos_per_legislature(con):
    rates = {leg: (a, r, round(a / (a + r) * 100, 1)) for leg, a, r in _deputy_projetos(con)}
    assert {leg: rates[leg] for leg in ("XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII")} == {
        "XI": (375, 301, 55.5),
        "XII": (701, 1456, 32.5),
        "XIII": (1407, 740, 65.5),
        "XIV": (579, 355, 62.0),
        "XV": (277, 1088, 20.3),
        "XVI": (312, 447, 41.1),
        "XVII": (421, 826, 33.8),
    }


def test_strict_rule_reproduces_the_review_figures(con):
    # The review's rate B: latest vote of the four original decisive phases by (date, vote_id),
    # no 'Votação final', plus generality rejections. Same release, same counts, so the gap to
    # this PR's figures comes only from 'Votação final' and point-by-point days.
    rows = con.execute(
        """
        with plenary as (
            select iv.initiative_legislature as legislature, iv.initiative_id, iv.phase, v.vote_id, v.date, v.result
            from initiative_votes iv join votes v on v.vote_id = iv.vote_id
            where iv.body = 'plenary'
        ),
        fin as (
            select legislature, initiative_id, max(date) as date,
                   arg_max(result, struct_pack(d := date, id := vote_id)) as result
            from plenary
            where phase in ('Votação final global', 'Votação final global decreto', 'Votação global',
                            'Votação Deliberação')
            group by all
        ),
        gen as (
            select legislature, initiative_id, max(date) as date,
                   arg_max(result, struct_pack(d := date, id := vote_id)) as result
            from plenary
            where phase in ('Votação na generalidade', 'Votação generalidade decreto')
            group by all
        ),
        o as (
            select legislature, initiative_id,
                   case when f.result = 'Aprovado' then 'A'
                        when f.result = 'Rejeitado' then 'R'
                        when g.result = 'Rejeitado' and (f.date is null or g.date > f.date) then 'R' end as res
            from fin f full join gen g using (legislature, initiative_id)
        )
        select i.legislature, count(*) filter (o.res = 'A'), count(*) filter (o.res = 'R')
        from initiatives i
        join (select distinct legislature, initiative_id from deputy_initiatives) d
          using (legislature, initiative_id)
        left join o using (legislature, initiative_id)
        where i.type_code in ('J', 'R', 'D')
        group by i.legislature
        """
    ).fetchall()
    rates = {leg: (a, r, round(a / (a + r) * 100, 1)) for leg, a, r in rows}
    assert {leg: rates[leg] for leg in ("XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII")} == {
        "XI": (366, 310, 54.1),
        "XII": (655, 1502, 30.4),
        "XIII": (1370, 777, 63.8),
        "XIV": (575, 359, 61.6),
        "XV": (270, 1095, 19.8),
        "XVI": (311, 448, 41.0),
        "XVII": (397, 797, 33.2),
    }


def test_approval_rate_per_type(con):
    rows = con.execute(
        """
        select i.legislature, i.type_code,
               round(100.0 * count(*) filter (o.result = 'Aprovado') / count(o.result), 1)
        from initiatives i
        join (select distinct legislature, initiative_id from deputy_initiatives) d
          on d.legislature = i.legislature and d.initiative_id = i.initiative_id
        left join initiative_outcome o on o.legislature = i.legislature and o.initiative_id = i.initiative_id
        where i.type_code in ('J', 'R') and i.legislature in ('XIII', 'XV', 'XVI', 'XVII')
        group by all
        """
    ).fetchall()
    assert {(leg, t): rate for leg, t, rate in rows} == {
        ("XIII", "J"): 46.3,
        ("XIII", "R"): 74.2,
        ("XV", "J"): 13.2,
        ("XV", "R"): 28.3,
        ("XVI", "J"): 23.6,
        ("XVI", "R"): 52.3,
        ("XVII", "J"): 15.3,
        ("XVII", "R"): 44.5,
    }


def test_point_by_point_votes_with_mixed_results(con):
    # Deputy-authored initiatives whose latest decisive day has both passed and failed votes.
    mixed = con.execute(
        """
        select count(*) from initiative_outcome o
        join (select distinct legislature, initiative_id from deputy_initiatives) d
          on d.legislature = o.legislature and d.initiative_id = o.initiative_id
        where o.partly_approved
        """
    ).fetchone()[0]
    assert mixed == 193


def test_deputy_approval_per_legislature(con):
    rows = deputies.detalhes(con, DEPUTY)["estatisticas"]["iniciativas_legislaturas"]
    got = {}
    for row in rows:
        approved = sum(t["aprovadas"] for t in row["aprovacao"])
        decided = sum(t["votadas"] for t in row["aprovacao"])
        got[row["legislatura"]] = (approved, decided, round(approved / decided * 100, 1))
    assert got["XVII"] == (24, 123, 19.5)
    assert got["XVI"] == (22, 86, 25.6)
    assert got["XV"] == (13, 201, 6.5)
    assert got["XIII"] == (225, 372, 60.5)
    xvii = next(r for r in rows if r["legislatura"] == "XVII")
    assert xvii["aberta"] is True
    assert sum(t["sem_votacao"] for t in xvii["aprovacao"]) == 115


def test_whole_group_lists_are_the_norm(con):
    rows = con.execute(
        """
        select legislature,
               round(100.0 * count(*) filter (kind = 'grupo_parlamentar')
                     / count(*) filter (kind in ('grupo_parlamentar', 'subscricao_restrita')), 1),
               count(*) filter (kind = 'outros_grupos')
        from initiative_signing
        where legislature in ('XIII', 'XIV', 'XV', 'XVI', 'XVII')
        group by legislature
        """
    ).fetchall()
    assert {leg: share for leg, share, _ in rows} == {
        "XIII": 55.8,
        "XIV": 68.2,
        "XV": 83.3,
        "XVI": 71.0,
        "XVII": 82.6,
    }
    # Deputies of more than one group: 98 initiatives list more than one author group, and 14
    # more list deputies of several groups without any author group.
    assert sum(n for _, _, n in rows) == 112


def test_deputy_signing_per_legislature(con):
    rows = deputies.detalhes(con, DEPUTY)["estatisticas"]["iniciativas_legislaturas"]
    got = {r["legislatura"]: tuple(r["assinatura"].values()) for r in rows}
    assert {leg: got[leg] for leg in ("XIII", "XIV", "XV", "XVI", "XVII")} == {
        "XIII": (103, 386, 3),
        "XIV": (187, 25, 0),
        "XV": (288, 6, 1),
        "XVI": (177, 0, 1),
        "XVII": (237, 0, 1),
    }


def test_comparison_population_is_seated_at_least_half(con):
    rows = con.execute(
        """
        select legislature, count(*), count(*) filter (days >= 0.5 * legislature_days)
        from deputy_seat_days where legislature in ('XV', 'XVI', 'XVII') group by legislature
        """
    ).fetchall()
    assert {leg: (people, half) for leg, people, half in rows} == {
        "XV": (274, 231),
        "XVI": (280, 230),
        "XVII": (270, 229),
    }


def test_deputy_group_is_too_small_to_compare(con):
    c = deputies.detalhes(con, DEPUTY)["estatisticas"]["comparacao"]
    assert c["iniciativas_subscricao_restrita"]["legislatura"] == "XVII"
    assert c["iniciativas_subscricao_restrita"]["pares"] == 2
    assert c["iniciativas_subscricao_restrita"]["nota"] == deputies.SMALL_GROUP
    assert c["intervencoes"]["legislatura"] == "XVI"
    assert c["intervencoes"]["media_grupo_por_ano"] is None


def test_declaration_flags_and_coverage(con):
    latest = con.execute(
        """
        select legislature, declaration_key from (
            select legislature, declaration_key, row_number() over (
                partition by legislature, cadastro_id
                order by version_date desc nulls last, declaration_id desc nulls last) as rn
            from interest_declarations
        ) where rn = 1
        """
    ).fetchall()
    flags = [repository.declaration_flags(con, leg, key) for leg, key in latest]
    assert len(flags) == 297
    assert sum(f["other_activities"] or f["shareholdings"] for f in flags) == 281  # 94.6%
    assert deputies.conflitos_interesse(con, DEPUTY)["cobertura"] == {
        "de": "XI",
        "ate": "XV",
        "com_declaracao": 297,
        "total": 1425,
    }
