"""#263: the decisions of the last day with plenary votes, checked by hand on a real release.

Skipped unless FISCALIZA_RELEASE_DIR points at a release folder. Pinned on data-2026-11-06
(manifest source_updated 2026-11-05), whose last plenary day is 2026-10-28, so the test skips on
any other tag. The expected set was read vote by vote from that day.
"""

import os
from pathlib import Path

import duckdb
import pytest

from app.data import repository
from fiscaliza_data import sync

RELEASE = os.environ.get("FISCALIZA_RELEASE_DIR")
TAG = "data-2026-11-06"
SOURCE_UPDATED = "2026-11-05"
DAY = "2026-10-28"

EXPECTED = {
    193246: "Votação na generalidade",  # Proposta de Lei 110/XVII, Orçamento do Estado para 2027
    # Projetos de resolução in a votação final
    193250: "Votação final",
    193251: "Votação final",
    193252: "Votação final",
    193253: "Votação final",
    193254: "Votação final",
    193255: "Votação final",
    193256: "Votação final",
    193257: "Votação final",
    193268: "Votação final global",  # Projeto de Lei 672/XVII
    193270: "Votação final global",  # Projeto de Lei 674/XVII
    193272: "Votação final global",  # Proposta de Lei 70/XVII, Grandes Opções
    193276: "Votação final global",  # Projeto de Lei 581/XVII (generality and specialty the same day: left out)
    193279: "Votação final global",  # Projeto de Lei 528/XVII (idem)
    193280: "Votação final global",  # Projeto de Resolução 1248/XVII
}

pytestmark = pytest.mark.skipif(not RELEASE, reason="FISCALIZA_RELEASE_DIR is not set")


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    result = sync.sync(tmp_path_factory.mktemp("release") / "data", from_dir=Path(RELEASE))
    if result.tag != TAG:
        pytest.skip(f"decisions are pinned on {TAG}, not {result.tag}")
    c = duckdb.connect(str(result.path), read_only=True)
    yield c
    c.close()


def test_the_release_is_the_cited_snapshot(con):
    assert str(repository.meta(con)["source_updated"]) == SOURCE_UPDATED


def test_last_day_decisions_match_the_hand_checked_set(con):
    assert str(repository.last_plenary_vote_day(con)) == DAY
    rows = repository.plenary_decisions(con, DAY)
    assert {r["vote_id"]: r["phase"] for r in rows} == EXPECTED
