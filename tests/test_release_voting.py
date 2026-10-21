"""Deputy vote positions checked by hand against the vote detail of a real release.

Skipped unless FISCALIZA_RELEASE_DIR points at a release folder (manifest.json and the Parquet
files, for example a local `release build` of parlamento-aberto). Pinned on data-2026-10-20,
so the test skips on any other tag. Ids only, no names.
"""

import os
from pathlib import Path

import duckdb
import pytest

from fiscaliza_data import sync

RELEASE = os.environ.get("FISCALIZA_RELEASE_DIR")
TAG = "data-2026-10-20"
DEPUTY = 8982  # a PS deputy in XVII with named dissents

# vote_id: position, each read from the vote's detail text.
CHECKED = {
    139172: "favour",  # named in favour while PS abstained (the 11-PS count is the 11 named)
    139190: "favour",  # PS in favour; the 1-PS abstention is one named deputy, not this one
    140052: None,  # every group given by counts only (54-PS against): unknown
    138959: None,  # no detail published
    138952: "favour",  # unanimous, no positions: inferred favour
    138954: "favour",
    138956: "against",
    138999: "against",
    139003: "abstention",
    171887: "favour",  # named in favour while PS abstained
}

pytestmark = pytest.mark.skipif(not RELEASE, reason="FISCALIZA_RELEASE_DIR is not set")


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    result = sync.sync(tmp_path_factory.mktemp("release") / "data", from_dir=Path(RELEASE))
    if result.tag != TAG:
        pytest.skip(f"positions are pinned on {TAG}, not {result.tag}")
    c = duckdb.connect(str(result.path), read_only=True)
    yield c
    c.close()


def test_positions_match_the_hand_checked_votes(con):
    rows = con.execute(
        "select vote_id, position from deputy_vote_positions where cadastro_id = ? and list_contains(?, vote_id)",
        [DEPUTY, list(CHECKED)],
    ).fetchall()
    assert dict(rows) == CHECKED
