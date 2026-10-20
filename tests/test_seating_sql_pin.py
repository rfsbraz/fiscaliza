"""fiscaliza_data/seating.sql must stay an unchanged copy of parlamento-aberto's macros.sql.

The copy starts with a short header comment, then a blank line, then the upstream file
byte for byte. The test hashes everything after the header and compares it with the
sha256 of src/parlamento_aberto/models/macros.sql at UPSTREAM_REF, recorded below, so it
runs offline. parlamento-aberto has no release tags yet, so the pin is a commit on main.

To refresh after parlamento-aberto changes macros.sql (or once a release tag carries it):

1. Copy the file at the new ref over everything below the header of seating.sql:
   gh api "repos/rfsbraz/parlamento-aberto/contents/src/parlamento_aberto/models/macros.sql?ref=<ref>" --jq .content | base64 -d
2. Get its sha256 by piping the same command into `sha256sum`.
3. Update UPSTREAM_REF and UPSTREAM_SHA256 below, and the ref named in the seating.sql header.
"""

import hashlib
from pathlib import Path

SEATING_SQL = Path(__file__).resolve().parent.parent / "fiscaliza_data" / "seating.sql"

UPSTREAM_REPO = "rfsbraz/parlamento-aberto"
UPSTREAM_PATH = "src/parlamento_aberto/models/macros.sql"
UPSTREAM_REF = "5980ed2bb8c952c9f4220c7cb94c6d78c5c64810"
UPSTREAM_SHA256 = "56b5e887a87598c71c747b5f6411bb5919a73f2b68f36c6241a6572073e4512a"


def _split():
    header, sep, body = SEATING_SQL.read_bytes().partition(b"\n\n")
    assert sep, "seating.sql needs a header comment, a blank line, then the copied file"
    return header.decode(), body


def test_header_names_the_pinned_upstream_file_and_ref():
    header, _ = _split()
    assert all(line.startswith("--") for line in header.splitlines())
    assert f"{UPSTREAM_REPO} {UPSTREAM_PATH}" in header
    assert UPSTREAM_REF[:7] in header


def test_copy_matches_upstream_macros_sql_at_the_pinned_ref():
    _, body = _split()
    assert hashlib.sha256(body).hexdigest() == UPSTREAM_SHA256, (
        f"seating.sql drifted from {UPSTREAM_REPO} {UPSTREAM_PATH} at {UPSTREAM_REF[:7]}; "
        "see this test's docstring to refresh it"
    )
