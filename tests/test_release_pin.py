"""The data pin, checked on a release built from it.

Skipped unless FISCALIZA_RELEASE_DIR points at a release folder (manifest.json and the Parquet
files), for example `release build` of parlamento-aberto at the commit in deploy/data-pin. The
figures are those of the pinned commit, so moving the pin means checking them again here. Only
counts and ids, no names.
"""

import importlib.util
import json
import os
from pathlib import Path

import duckdb
import pytest

from app.services import core, deputies
from fiscaliza_data import sync

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

RELEASE = os.environ.get("FISCALIZA_RELEASE_DIR")
I_A_ONLY = 3783  # sat in the Constituinte only, from 1976-06-03 to 1978-08-28 (#108)

pytestmark = pytest.mark.skipif(not RELEASE, reason="FISCALIZA_RELEASE_DIR is not set")


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    result = sync.sync(tmp_path_factory.mktemp("release") / "data", from_dir=Path(RELEASE))
    c = duckdb.connect(str(result.path), read_only=True)
    yield c
    c.close()


def test_the_release_is_built_from_the_pin():
    manifest = json.loads((Path(RELEASE) / "manifest.json").read_text())
    assert manifest["data_commit"] == pages.read_pin().commit


def test_constituinte_parts_keep_only_their_own_periods(con):
    # parlamento-aberto #88: I-A and I-B no longer carry the same 893 mandate rows.
    mandates = con.execute(
        """
        select legislature, count(*), count(distinct cadastro_id)
        from mandates where legislature in ('I-A', 'I-B') group by 1 order by 1
        """
    ).fetchall()
    assert mandates == [("I-A", 626, 486), ("I-B", 382, 326)]
    memberships = con.execute(
        "select legislature, count(*) from group_memberships where legislature in ('I-A', 'I-B') group by 1 order by 1"
    ).fetchall()
    assert memberships == [("I-A", 429), ("I-B", 326)]


def test_constituinte_deputies_are_not_counted_twice_on_the_site(con):
    totals = {leg["numero"]: leg["total_deputados"] for leg in core.legislaturas(con)["legislaturas"]}
    assert (totals["I-A"], totals["I-B"]) == (486, 326)
    stats = deputies.detalhes(con, I_A_ONLY)["estatisticas"]
    assert (stats["total_mandatos"], stats["legislaturas_servidas"]) == (1, "I-A")


def test_cdu_note_is_the_same_in_xv_xvi_and_xvii(con):
    # parlamento-aberto #87: XVI had "PPM won no seat.", which is not about the CDU.
    notes = con.execute(
        "select distinct note from coalitions where coalition = 'CDU' and legislature in ('XV', 'XVI', 'XVII')"
    ).fetchall()
    assert len(notes) == 1
