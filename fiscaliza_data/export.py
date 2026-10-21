"""Render the site API to static JSON files, so any static host can serve the site.

    python -m fiscaliza_data.export --out DIR [--data-dir DIR] [--jobs N]

Run it after `python -m fiscaliza_data sync`: it reads the live DuckDB file and writes one JSON
file per answer the frontend needs into a fresh folder, then swaps it in for the old one. The
frontend (frontend/src/config/staticApi.js) maps each API request to its file and does the
rest in the browser: deputy search over one index file, and filtering, sorting and paging a
deputy's interventions. docs/STATIC_EXPORT.md has the layout and how to serve it.

Path form: legislatures, parties and coalitions appear in paths as ``slug(name)``: accents
dropped, lowercase, and every run of other characters (slashes, spaces) turned into one
dash. So XVII is ``xvii``, PàF is ``paf`` and MDP/CDE is ``mdp-cde``. Two names that give
the same path stop the export.

Everything about one deputy (details, interest register, interventions and initiatives for
each legislature, voting analytics for each legislature) is one file, so the count grows
with people, not people times legislatures: about 3,400 files on the full release. The export
fails before swapping if it reaches MAX_FILES files or any file reaches MAX_FILE_BYTES, limits
that fit the common static hosts.

Not rendered yet: attendance (S11) and the agenda for today and this week (S13). The browser
answers them "not available" until their marts land; then they get files here the same way.
The deputy and party endpoints of S5, S6 and S7 render once their services are on master
(app.services.deputies, voting and parties); until then their files are left out.
"""

import argparse
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import duckdb

from fiscaliza_data.sync import DEFAULT_DATA_DIR

CURRENT = "current.duckdb"
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024
# The limits the frontend sends, rendered one file each.
RECENT_VOTES = (5, 10)
CHUNK = 50


class ExportError(Exception):
    """The export could not be rendered; the previous output is left as it was."""


@dataclass
class ExportResult:
    out: Path
    files: int
    bytes: int
    largest: tuple


def slug(value):
    """The path form of a legislature, party or coalition name."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        raise ExportError(f"{value!r} has no path form")
    return text


def slugs(names):
    """{name: slug} for distinct names, refusing two that share a path."""
    out, seen = {}, {}
    for name in names:
        s = slug(name)
        if s in seen and seen[s] != name:
            raise ExportError(f"{seen[s]!r} and {name!r} have the same path {s!r}")
        seen[s], out[name] = name, s
    return out


def _optional(name):
    """A service module that is not on master yet (S5 to S7), or None."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name != name:
            raise
        return None


def _services():
    from app.services import activity, core

    return {
        "core": core,
        "activity": activity,
        "deputies": _optional("app.services.deputies"),
        "voting": _optional("app.services.voting"),
        "parties": _optional("app.services.parties"),
    }


def _json_default(value):
    # As Flask's JSON provider writes them.
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"{type(value).__name__} is not JSON serialisable")


def _dump(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default).encode()


class _Writer:
    def __init__(self, root):
        self.root = Path(root)
        self.files = []

    def write(self, path, payload):
        data = _dump(payload)
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.files.append((path, len(data)))


def _all_pages(fetch, key, per_page):
    """Every item of a paged service answer, with the first page's payload."""
    first = fetch(1, per_page)
    items = list(first[key])
    meta = first.get("pagination") or first.get("intervention_metadata")
    for page in range(2, meta["pages"] + 1):
        items += fetch(page, per_page)[key]
    return first, items


def _not_found(svc):
    return svc["core"].NotFound


# Site-wide files


def _site_files(con, svc, w):
    core, activity = svc["core"], svc["activity"]
    w.write("legislaturas.json", core.legislaturas(con))
    w.write("estatisticas.json", core.estatisticas(con))
    w.write("estatisticas/atividade.json", activity.estatisticas_atividade(con))
    w.write("partidos.json", core.partidos(con))
    w.write("health.json", core.health(con))
    for limit in RECENT_VOTES:
        w.write(f"votacoes/recentes/{limit}.json", activity.votacoes_recentes(con, limite=limit))

    w.write("coligacoes.json", core.coligacoes(con, include_inactive=False))
    every = core.coligacoes(con, include_inactive=True)
    w.write("coligacoes-todas.json", every)
    for sigla, s in slugs(c["sigla"] for c in every["coligacoes"]).items():
        w.write(f"coligacoes/{s}.json", core.coligacao(con, sigla))
        w.write(f"coligacoes/{s}/deputados.json", core.coligacao_deputados(con, sigla))
        w.write(f"coligacoes/{s}/partidos.json", core.coligacao_partidos(con, sigla))

    _deputy_index(con, core, w)
    _party_files(con, svc, w)


def _deputy_index(con, core, w):
    """Everyone the deputies page can list, in its order, for search and paging in the browser.
    ``registos`` is each person's number of legislatures, for the records count of a search."""
    first, people = _all_pages(
        lambda page, per_page: core.deputados(con, page=page, per_page=per_page, active_only=False),
        "deputados",
        core.MAX_PER_PAGE,
    )
    counts = dict(con.execute("select cadastro_id, count(*) from deputy_legislatures group by 1").fetchall())
    w.write(
        "deputados.json",
        {
            "deputados": people,
            "registos": [counts[p["id_cadastro"]] for p in people],
            "filters": {
                "active_deputies_count": first["filters"]["active_deputies_count"],
                "seated_deputies_count": first["filters"]["seated_deputies_count"],
            },
        },
    )


def _party_files(con, svc, w):
    parties, voting = svc["parties"], svc["voting"]
    if parties is None and voting is None:
        return
    rows = con.execute("select legislature, group_acronym from parliamentary_groups").fetchall()
    groups = slugs(sorted({g for _, g in rows}))
    legs = slugs(sorted({leg for leg, _ in rows}))
    NotFound = _not_found(svc)
    for sigla, s in groups.items():
        if parties is not None:
            try:
                w.write(f"partidos/{s}/deputados.json", parties.partido_deputados(con, sigla))
            except NotFound:
                pass
        if voting is not None:
            try:
                w.write(f"partidos/{s}/voting-analytics.json", voting.partido_voting_analytics(con, sigla))
            except NotFound:
                pass
            for leg in sorted({leg for leg, g in rows if g == sigla}):
                try:
                    payload = voting.partido_voting_analytics(con, sigla, leg)
                except NotFound:
                    continue
                w.write(f"partidos/{s}/voting-analytics/{legs[leg]}.json", payload)


# One file per deputy


def _activities(deputies, con, cadastro_id, legislature):
    """The activities answer for a legislature with every intervention, newest first; the
    browser filters, sorts and pages them."""
    per_page = deputies.MAX_PER_PAGE
    first, items = _all_pages(
        lambda page, n: deputies.atividades(con, cadastro_id, legislatura=legislature, page=page, per_page=n),
        "intervencoes",
        per_page,
    )
    first = dict(first)
    first.pop("intervention_metadata")
    first["intervencoes"] = items
    return first


def deputy_bundle(con, svc, cadastro_id):
    """Everything the deputy page reads about one person."""
    deputies, voting = svc["deputies"], svc["voting"]
    legs = [
        r[0]
        for r in con.execute(
            """
            select dl.legislature from deputy_legislatures dl
            join legislature_days l using (legislature)
            where dl.cadastro_id = ? order by l.start_date
            """,
            [cadastro_id],
        ).fetchall()
    ]
    bundle = {"id_cadastro": cadastro_id, "legislatura_atual": legs[-1]}
    if deputies is not None:
        bundle["detalhes"] = deputies.detalhes(con, cadastro_id)
        bundle["conflitos_interesse"] = deputies.conflitos_interesse(con, cadastro_id)
        bundle["atividades"] = {leg: _activities(deputies, con, cadastro_id, leg) for leg in legs}
    if voting is not None:
        found = {}
        for leg in legs:
            try:
                found[leg] = voting.deputado_voting_analytics(con, cadastro_id, leg)
            except _not_found(svc):
                pass
        bundle["voting_analytics"] = found
    return bundle


def _deputy_chunk(args):
    db, root, ids = args
    svc = _services()
    w = _Writer(root)
    con = duckdb.connect(db, read_only=True)
    try:
        for cadastro_id in ids:
            w.write(f"deputados/{cadastro_id}.json", deputy_bundle(con, svc, cadastro_id))
    finally:
        con.close()
    return w.files


def _deputy_files(db, con, svc, root, jobs):
    if svc["deputies"] is None and svc["voting"] is None:
        return []
    ids = [r[0] for r in con.execute("select distinct cadastro_id from deputy_legislatures order by 1").fetchall()]
    chunks = [(db, str(root), ids[i : i + CHUNK]) for i in range(0, len(ids), CHUNK)]
    if jobs <= 1:
        return [f for chunk in chunks for f in _deputy_chunk(chunk)]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return [f for files in pool.map(_deputy_chunk, chunks) for f in files]


# The whole export


def _check(files):
    if len(files) >= MAX_FILES:
        raise ExportError(f"{len(files)} files, the limit is under {MAX_FILES}")
    path, size = max(files, key=lambda f: f[1])
    if size >= MAX_FILE_BYTES:
        raise ExportError(f"{path} is {size} bytes, the limit is under {MAX_FILE_BYTES}")
    return path, size


def export(data_dir=DEFAULT_DATA_DIR, out="static/api", jobs=1):
    """Render every answer into a new folder next to ``out`` and swap it in. On any error the
    previous ``out`` stays untouched."""
    db = Path(data_dir) / CURRENT
    if not db.is_file():
        raise ExportError(f"no data file at {db}; run `python -m fiscaliza_data sync` first")
    out = Path(out).absolute()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        svc = _services()
        w = _Writer(work)
        con = duckdb.connect(str(db), read_only=True)
        try:
            _site_files(con, svc, w)
            files = w.files + _deputy_files(str(db), con, svc, work, jobs)
        finally:
            con.close()
        largest = _check(files)
        old = None
        if out.exists():
            old = out.with_name(f".{out.name}-old")
            shutil.rmtree(old, ignore_errors=True)
            out.rename(old)
        work.rename(out)
        if old is not None:
            shutil.rmtree(old, ignore_errors=True)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return ExportResult(out=out, files=len(files), bytes=sum(s for _, s in files), largest=largest)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m fiscaliza_data.export", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="folder to write; replaced as a whole when the render succeeds")
    parser.add_argument(
        "--data-dir",
        default=os.getenv("FISCALIZA_DATA_DIR") or DEFAULT_DATA_DIR,
        help=f"where the live DuckDB file is (default $FISCALIZA_DATA_DIR, else {DEFAULT_DATA_DIR})",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="processes for the deputy files")
    args = parser.parse_args(argv)
    try:
        result = export(args.data_dir, args.out, jobs=args.jobs)
    except ExportError as e:
        print(f"export failed: {e}", file=sys.stderr)
        return 1
    path, size = result.largest
    print(
        f"{result.files} files, {result.bytes / 2**20:.1f} MiB in {result.out}; largest {path} ({size / 2**20:.2f} MiB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
