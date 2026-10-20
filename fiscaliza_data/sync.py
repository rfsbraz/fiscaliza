"""Turn a parlamento-aberto data release into the site's local, read-only DuckDB file.

1. Find the release: a tag, the latest release on GitHub, or a local `release build` folder.
2. Stop if that tag is already live.
3. Get manifest.json and every Parquet file it lists; check each SHA-256.
4. Refuse a schema_version whose major the site does not support.
5. Load the Parquet files as tables into a new fiscaliza-<tag>.duckdb, with the seating
   macros, the site views (views.sql) and a _meta table.
6. Smoke checks: the current legislature has 230 seated deputies at its extract date, and
   no table has more than 5% fewer rows than in the live file.
7. Point current.duckdb at the new file atomically and keep only the last two files.

Any failure raises SyncError and leaves the previous file live.
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import requests

DEFAULT_DATA_DIR = "data"
REPO = "rfsbraz/parlamento-aberto"
API = f"https://api.github.com/repos/{REPO}/releases"
SUPPORTED_SCHEMA_MAJOR = 1
SEATS = 230
MAX_DROP = 0.05
KEEP = 2
CURRENT = "current.duckdb"
SEATING_SQL = Path(__file__).with_name("seating.sql")
VIEWS_SQL = Path(__file__).with_name("views.sql")
_TAG = re.compile(r"^[A-Za-z0-9._-]+$")
_MART = re.compile(r"^[a-z][a-z0-9_]*$")


class SyncError(Exception):
    """The release cannot go live. The previous file stays live."""


@dataclass
class Result:
    tag: str
    changed: bool
    path: Path | None = None
    extract_date: str | None = None
    seated: dict = field(default_factory=dict)


class Http:
    """Unauthenticated GitHub access: one API call, then plain asset downloads."""

    def __init__(self, timeout=60):
        self.timeout = timeout

    def get_json(self, url):
        r = requests.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=self.timeout)
        if r.status_code != 200:
            raise SyncError(f"GET {url}: HTTP {r.status_code}")
        return r.json()

    def download(self, url, dest):
        with requests.get(url, stream=True, timeout=self.timeout) as r:
            if r.status_code != 200:
                raise SyncError(f"GET {url}: HTTP {r.status_code}")
            with dest.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_name(tag):
    return f"fiscaliza-{tag}.duckdb"


def live_tag(data_dir):
    current = Path(data_dir) / CURRENT
    if not current.exists():
        return None
    con = duckdb.connect(str(current), read_only=True)
    try:
        return con.execute("select tag from _meta").fetchone()[0]
    finally:
        con.close()


def _check_tag(tag):
    if not _TAG.match(tag or ""):
        raise SyncError(f"bad release tag {tag!r}")
    return tag


def _check_schema(manifest):
    version = str(manifest.get("schema_version", ""))
    major = version.split(".", 1)[0]
    if not major.isdigit() or int(major) != SUPPORTED_SCHEMA_MAJOR:
        raise SyncError(
            f"schema_version {version or '(none)'} is not supported; this site reads {SUPPORTED_SCHEMA_MAJOR}.x"
        )


def _parquet_files(manifest):
    """{mart: (file name, sha256)} from the manifest."""
    marts = manifest.get("marts")
    if not isinstance(marts, dict) or not marts:
        raise SyncError("manifest.json lists no marts")
    out = {}
    for mart, entry in marts.items():
        if not _MART.match(mart):
            raise SyncError(f"bad mart name {mart!r} in manifest.json")
        parquet = (entry.get("files") or {}).get("parquet") or {}
        name, sha = parquet.get("name"), parquet.get("sha256")
        if name != f"{mart}.parquet" or not sha:
            raise SyncError(f"manifest.json has no Parquet file and hash for {mart}")
        out[mart] = (name, sha)
    return out


def _verify(folder, files):
    for name, sha in files.values():
        path = folder / name
        if not path.is_file():
            raise SyncError(f"{name}: missing from the release")
        if _sha256(path) != sha:
            raise SyncError(f"{name}: SHA-256 does not match manifest.json")


def _build(path, folder, manifest, files):
    con = duckdb.connect(str(path))
    try:
        for mart, (name, _) in files.items():
            # mart names are checked against _MART in _parquet_files
            con.execute(f"create table {mart} as select * from read_parquet(?)", [str(folder / name)])  # noqa: S608
        macros = folder / "macros.sql"
        con.execute((macros if macros.is_file() else SEATING_SQL).read_text(encoding="utf-8"))
        con.execute(VIEWS_SQL.read_text(encoding="utf-8"))
        con.execute(
            "create table _meta as select ?::varchar as tag, ?::varchar as schema_version, "
            "?::varchar as source_updated, ?::varchar as data_commit, now() as synced_at",
            [
                manifest["tag"],
                str(manifest["schema_version"]),
                manifest.get("source_updated"),
                manifest.get("data_commit"),
            ],
        )
        con.execute("checkpoint")
    finally:
        con.close()


def _smoke(path, live):
    """Return (extract date, {legislature: seated}); raise SyncError if a check fails."""
    con = duckdb.connect(str(path), read_only=True)
    try:
        row = con.execute(
            "select legislature, extract_date from legislatures where end_date is null order by start_date desc limit 1"
        ).fetchone()
        if row is None or row[1] is None:
            raise SyncError("no current legislature with an extract date")
        legislature, day = row
        seated = con.execute(
            "select count(*) from seated_on(?::date) where legislature = ?", [day, legislature]
        ).fetchone()[0]
        if seated != SEATS:
            raise SyncError(f"{legislature} has {seated} seated deputies on {day}, expected {SEATS}")
        if live is not None:
            new_counts = _counts(con)
            old = duckdb.connect(str(live), read_only=True)
            try:
                old_counts = _counts(old)
            finally:
                old.close()
            for table, before in sorted(old_counts.items()):
                after = new_counts.get(table)
                if after is None:
                    raise SyncError(f"{table}: missing, the live file has it")
                if before and after < before * (1 - MAX_DROP):
                    raise SyncError(f"{table}: {after} rows, {before} live (more than {MAX_DROP:.0%} fewer)")
        return str(day), {legislature: seated}
    finally:
        con.close()


def _counts(con):
    tables = [
        r[0]
        for r in con.execute(
            "select table_name from information_schema.tables where table_schema = 'main' and table_type = 'BASE TABLE'"
        ).fetchall()
        if not r[0].startswith("_")
    ]
    # table names come from information_schema of a file we just built
    return {t: con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}  # noqa: S608


def _swap(data_dir, name):
    tmp = data_dir / f".{CURRENT}.{os.getpid()}"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(name)
    os.replace(tmp, data_dir / CURRENT)


def _prune(data_dir, live_name):
    """Keep the live file and the newest other one (the previous release)."""
    others = sorted(
        (p for p in data_dir.glob("fiscaliza-*.duckdb") if p.name != live_name),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    for p in others[KEEP - 1 :]:
        p.unlink()


def _from_github(tag, http, data_dir, live):
    url = f"{API}/tags/{tag}" if tag else f"{API}/latest"
    release = http.get_json(url)
    found = _check_tag(release.get("tag_name"))
    if tag and found != tag:
        raise SyncError(f"asked for {tag}, GitHub returned {found}")
    if found == live:
        return found, None
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    if "manifest.json" not in assets:
        raise SyncError(f"release {found} has no manifest.json")
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=data_dir))
    http.download(assets["manifest.json"], staging / "manifest.json")
    manifest = _read_manifest(staging)
    _check_schema(manifest)
    files = _parquet_files(manifest)
    for name, _ in files.values():
        if name not in assets:
            raise SyncError(f"{name}: missing from the release")
        http.download(assets[name], staging / name)
    if "macros.sql" in assets:
        http.download(assets["macros.sql"], staging / "macros.sql")
    return found, staging


def _read_manifest(folder):
    try:
        return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SyncError(f"cannot read manifest.json: {e}") from None


def sync(data_dir=DEFAULT_DATA_DIR, tag=None, from_dir=None, http=None):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    live = live_tag(data_dir)
    staging = None
    building = None
    try:
        if from_dir:
            folder = Path(from_dir)
            manifest = _read_manifest(folder)
            found = _check_tag(manifest.get("tag"))
            if tag and found != tag:
                raise SyncError(f"asked for {tag}, {folder} holds {found}")
            if found == live:
                return Result(tag=found, changed=False)
        else:
            found, staging = _from_github(tag, http or Http(), data_dir, live)
            if staging is None:
                return Result(tag=found, changed=False)
            folder = staging
            manifest = _read_manifest(folder)
        if manifest.get("tag") != found:
            raise SyncError(f"manifest.json says {manifest.get('tag')}, the release is {found}")
        _check_schema(manifest)
        files = _parquet_files(manifest)
        _verify(folder, files)
        name = _file_name(found)
        building = data_dir / f".{name}.building"
        if building.exists():
            building.unlink()
        _build(building, folder, manifest, files)
        live_path = (data_dir / CURRENT) if live else None
        extract_date, seated = _smoke(building, live_path)
        os.replace(building, data_dir / name)
        building = None
        _swap(data_dir, name)
        _prune(data_dir, name)
        return Result(tag=found, changed=True, path=data_dir / name, extract_date=extract_date, seated=seated)
    except duckdb.Error as e:
        raise SyncError(f"DuckDB: {e}") from None
    finally:
        if building is not None and building.exists():
            building.unlink()
            wal = building.with_name(building.name + ".wal")
            if wal.exists():
                wal.unlink()
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
