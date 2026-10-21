"""Sync tool: build the site's DuckDB file from a parlamento-aberto release.

Every test builds a tiny release in tmp_path (a few Parquet files and a manifest). No
network: the GitHub path uses a fake HTTP client.
"""

import hashlib
import json
import os
from pathlib import Path

import duckdb
import pytest

from fiscaliza_data import sync
from fiscaliza_data.__main__ import main

SEATS = 230


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_release(root, tag="data-2026-10-20", seated=SEATS, extra_rows=0, schema="1.1.0"):
    """A release folder like `release build` writes, with XVII and `seated` deputies."""
    out = Path(root) / tag
    out.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        "create table legislatures as select 'XVII' as legislature, 17 as legislature_id, "
        "date '2025-06-03' as start_date, null::date as end_date, date '2026-10-19' as extract_date"
    )
    con.execute(
        "create table mandates as select 'XVII' as legislature, i::bigint as cadastro_id, "
        "(1000 + i)::bigint as deputy_id, (i % 22)::int as circle_id, 'Efetivo' as situation, "
        "true as is_effective, date '2025-06-03' as start_date, null::date as end_date "
        "from range(?) t(i)",
        [seated],
    )
    con.execute(
        "create table deputies as select i::bigint as cadastro_id, 'Deputado ' || i as name from range(?) t(i)",
        [SEATS + extra_rows],
    )
    # The site views (views.sql) also read these; empty is enough here.
    con.execute(
        "create table group_memberships (legislature varchar, cadastro_id bigint, group_id integer, "
        "group_acronym varchar, start_date date, end_date date, is_open boolean)"
    )
    con.execute("create table electoral_circles (legislature varchar, circle_id integer, name varchar)")
    con.execute("create table parliamentary_groups (legislature varchar, group_acronym varchar, name varchar)")
    con.execute(
        "create table initiative_authors (legislature varchar, initiative_id bigint, author_type varchar, "
        "cadastro_id bigint, group_code varchar, name varchar)"
    )
    con.execute(
        "create table initiative_votes (vote_id bigint, initiative_id bigint, initiative_legislature varchar, "
        "body varchar, phase varchar)"
    )
    con.execute("create table votes (vote_id bigint, legislature varchar, date date, body varchar, result varchar)")
    marts = {}
    for mart in (
        "legislatures",
        "mandates",
        "deputies",
        "group_memberships",
        "electoral_circles",
        "parliamentary_groups",
        "initiative_authors",
        "initiative_votes",
        "votes",
    ):
        path = out / f"{mart}.parquet"
        con.execute(f"copy {mart} to '{path}' (format parquet)")
        rows = con.execute(f"select count(*) from {mart}").fetchone()[0]  # noqa: S608
        marts[mart] = {"rows": rows, "files": {"parquet": {"name": path.name, "sha256": _sha(path)}}}
    manifest = {"tag": tag, "schema_version": schema, "source_updated": "2026-10-20", "marts": marts}
    (out / "manifest.json").write_text(json.dumps(manifest))
    return out


def live_tag(data_dir):
    current = Path(data_dir) / "current.duckdb"
    if not current.exists():
        return None
    con = duckdb.connect(str(current), read_only=True)
    try:
        return con.execute("select tag from _meta").fetchone()[0]
    finally:
        con.close()


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    return d


def test_happy_path_builds_and_swaps_in_the_new_file(tmp_path, data_dir):
    release = make_release(tmp_path / "rel")
    result = sync.sync(data_dir, from_dir=release)
    assert result.changed and result.tag == "data-2026-10-20"
    assert result.seated == {"XVII": SEATS}
    current = data_dir / "current.duckdb"
    assert current.is_symlink()
    assert os.readlink(current) == "fiscaliza-data-2026-10-20.duckdb"
    assert live_tag(data_dir) == "data-2026-10-20"
    con = duckdb.connect(str(current), read_only=True)
    assert con.execute("select count(*) from deputies").fetchone()[0] == SEATS
    meta = con.execute("select schema_version, source_updated from _meta").fetchone()
    assert meta == ("1.1.0", "2026-10-20")


def test_seating_macro_is_available_in_the_built_file(tmp_path, data_dir):
    sync.sync(data_dir, from_dir=make_release(tmp_path / "rel"))
    con = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    n = con.execute("select count(*) from seated_on(date '2026-10-19') where legislature = 'XVII'")
    assert n.fetchone()[0] == SEATS


def test_unchanged_tag_does_nothing(tmp_path, data_dir):
    release = make_release(tmp_path / "rel")
    sync.sync(data_dir, from_dir=release)
    before = (data_dir / "fiscaliza-data-2026-10-20.duckdb").stat().st_mtime_ns
    result = sync.sync(data_dir, from_dir=release)
    assert not result.changed
    assert (data_dir / "fiscaliza-data-2026-10-20.duckdb").stat().st_mtime_ns == before
    assert sorted(p.name for p in data_dir.iterdir()) == ["current.duckdb", "fiscaliza-data-2026-10-20.duckdb"]


def _live_then_fail(tmp_path, data_dir, **bad):
    sync.sync(data_dir, from_dir=make_release(tmp_path / "old", tag="data-2026-10-19"))
    release = make_release(tmp_path / "new", **bad)
    return release


def _assert_previous_still_live(data_dir):
    assert live_tag(data_dir) == "data-2026-10-19"
    assert sorted(p.name for p in data_dir.iterdir()) == ["current.duckdb", "fiscaliza-data-2026-10-19.duckdb"]


def test_tampered_hash_leaves_the_previous_file_live(tmp_path, data_dir):
    release = _live_then_fail(tmp_path, data_dir)
    with (release / "deputies.parquet").open("ab") as f:
        f.write(b"tampered")
    with pytest.raises(sync.SyncError, match="deputies.parquet: SHA-256 does not match"):
        sync.sync(data_dir, from_dir=release)
    _assert_previous_still_live(data_dir)


def test_unsupported_schema_major_leaves_the_previous_file_live(tmp_path, data_dir):
    release = _live_then_fail(tmp_path, data_dir, schema="2.0.0")
    with pytest.raises(sync.SyncError, match="schema_version 2.0.0"):
        sync.sync(data_dir, from_dir=release)
    _assert_previous_still_live(data_dir)


def test_failing_seat_check_leaves_the_previous_file_live(tmp_path, data_dir):
    release = _live_then_fail(tmp_path, data_dir, seated=229)
    with pytest.raises(sync.SyncError, match="XVII has 229 seated deputies on 2026-10-19, expected 230"):
        sync.sync(data_dir, from_dir=release)
    _assert_previous_still_live(data_dir)


def test_row_count_drop_over_five_percent_leaves_the_previous_file_live(tmp_path, data_dir):
    sync.sync(data_dir, from_dir=make_release(tmp_path / "old", tag="data-2026-10-19", extra_rows=100))
    release = make_release(tmp_path / "new")
    with pytest.raises(sync.SyncError, match="deputies: 230 rows, 330 live"):
        sync.sync(data_dir, from_dir=release)
    _assert_previous_still_live(data_dir)


def test_missing_parquet_leaves_the_previous_file_live(tmp_path, data_dir):
    release = _live_then_fail(tmp_path, data_dir)
    (release / "mandates.parquet").unlink()
    with pytest.raises(sync.SyncError, match="mandates.parquet"):
        sync.sync(data_dir, from_dir=release)
    _assert_previous_still_live(data_dir)


def test_tag_that_does_not_match_the_folder_is_refused(tmp_path, data_dir):
    release = make_release(tmp_path / "rel")
    with pytest.raises(sync.SyncError, match="data-2026-10-21"):
        sync.sync(data_dir, from_dir=release, tag="data-2026-10-21")
    assert list(data_dir.iterdir()) == []


def test_keeps_only_the_last_two_files(tmp_path, data_dir):
    for day in ("17", "18", "19", "20"):
        sync.sync(data_dir, from_dir=make_release(tmp_path / day, tag=f"data-2026-10-{day}"))
    assert sorted(p.name for p in data_dir.iterdir()) == [
        "current.duckdb",
        "fiscaliza-data-2026-10-19.duckdb",
        "fiscaliza-data-2026-10-20.duckdb",
    ]
    assert live_tag(data_dir) == "data-2026-10-20"


class FakeHttp:
    """Serves a release folder the way the GitHub API and asset downloads would."""

    def __init__(self, release):
        self.release = release
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        assets = [
            {"name": p.name, "browser_download_url": f"https://example.invalid/{p.name}"}
            for p in sorted(self.release.iterdir())
        ]
        return {"tag_name": self.release.name, "assets": assets}

    def download(self, url, dest):
        self.calls.append(url)
        dest.write_bytes((self.release / url.rsplit("/", 1)[1]).read_bytes())


def test_latest_release_from_github(tmp_path, data_dir):
    http = FakeHttp(make_release(tmp_path / "rel"))
    result = sync.sync(data_dir, http=http)
    assert result.changed and live_tag(data_dir) == "data-2026-10-20"
    assert http.calls[0] == "https://api.github.com/repos/rfsbraz/parlamento-aberto/releases/latest"
    assert all(not c.endswith(".csv.gz") for c in http.calls)


def test_named_tag_from_github(tmp_path, data_dir):
    http = FakeHttp(make_release(tmp_path / "rel"))
    sync.sync(data_dir, tag="data-2026-10-20", http=http)
    assert http.calls[0] == "https://api.github.com/repos/rfsbraz/parlamento-aberto/releases/tags/data-2026-10-20"


def test_github_unchanged_tag_downloads_nothing(tmp_path, data_dir):
    release = make_release(tmp_path / "rel")
    sync.sync(data_dir, from_dir=release)
    http = FakeHttp(release)
    assert not sync.sync(data_dir, http=http).changed
    assert len(http.calls) == 1


def test_cli_exits_non_zero_with_a_clear_message(tmp_path, data_dir, capsys):
    release = make_release(tmp_path / "rel", schema="2.0.0")
    assert main(["sync", "--from-dir", str(release), "--data-dir", str(data_dir)]) == 1
    err = capsys.readouterr().err
    assert "sync failed:" in err and "schema_version 2.0.0" in err


def test_cli_reports_seats(tmp_path, data_dir, capsys):
    release = make_release(tmp_path / "rel")
    assert main(["sync", "--from-dir", str(release), "--data-dir", str(data_dir)]) == 0
    out = capsys.readouterr().out
    assert "data-2026-10-20 is live" in out and "XVII: 230 seated" in out
    assert main(["sync", "--from-dir", str(release), "--data-dir", str(data_dir)]) == 0
    assert "already live" in capsys.readouterr().out
