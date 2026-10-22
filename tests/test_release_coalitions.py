"""Coalition counts checked on a real parlamento-aberto release (#197).

Skipped unless FISCALIZA_RELEASE_DIR points at a release folder. No figures are pinned: every
coalition list must have as many deputies elected as the seats it won, in every legislature
with seats per circle, whatever the tag. Only counts, no names.
"""

import os
from pathlib import Path

import duckdb
import pytest

from app.services import core
from fiscaliza_data import sync

RELEASE = os.environ.get("FISCALIZA_RELEASE_DIR")

pytestmark = pytest.mark.skipif(not RELEASE, reason="FISCALIZA_RELEASE_DIR is not set")


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    result = sync.sync(tmp_path_factory.mktemp("release") / "data", from_dir=Path(RELEASE))
    c = duckdb.connect(str(result.path), read_only=True)
    yield c
    c.close()


def _seats(con, legislature, ballots):
    return con.execute(
        "select sum(seats) from ballot_list_seats where legislature = ? and list_contains(?, ballot_acronym)",
        [legislature, list(ballots)],
    ).fetchone()[0]


def test_every_coalition_list_has_exactly_its_seats(con):
    checked = 0
    for c in core.coligacoes(con, include_inactive=True)["coligacoes"]:
        for leg in core.coligacao(con, c["id"])["legislaturas"]:
            seats = _seats(con, leg["legislatura"], leg["listas"])
            if seats is None:
                assert leg["contagem"] == "em_funcoes", (c["id"], leg["legislatura"])
                continue
            assert leg["contagem"] == "eleitos", (c["id"], leg["legislatura"])
            assert leg["deputados"] == seats, (c["id"], leg["legislatura"])
            listed = core.coligacao_deputados(con, c["id"], leg["legislatura"])
            assert listed["total_deputados"] == len(listed["deputados"]) == seats, (c["id"], leg["legislatura"])
            checked += 1
    assert checked > 0
