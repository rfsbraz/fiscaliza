"""A small synthetic parlamento-aberto release, built into the site's DuckDB file.

Ids and made-up names only, no real people. Two legislatures:

- XVI, closed (2024-03-26 to 2025-06-02): people 1 to 50 and 300 to 479 hold its 230 seats.
- XVII, open, extract date 2026-10-19: people 1 to 229 and 232 hold its 230 seats with the
  known split (KNOWN_SPLIT). Person 231 sat for PS until 2025-12-31 and resigned; person 232 took
  the seat on 2026-01-01. Person 500 is a substitute who never sat.

Person 1 sat for PS in XVI and for PSD in XVII. Coalitions: AD (PSD, CDS-PP) and CDU (PCP)
in both legislatures, and FRS (PS) in XVI only. Votes, initiatives and interventions for the
agenda page are in tests/site_agenda.py.
"""

import hashlib
import json
from pathlib import Path

import duckdb

from fiscaliza_data import sync
from tests.site_agenda import agenda_tables

TAG = "data-2026-10-20"
EXTRACT = "2026-10-19"
KNOWN_SPLIT = {
    "PSD": 89,
    "CH": 60,
    "PS": 58,
    "IL": 9,
    "L": 6,
    "PCP": 3,
    "CDS-PP": 2,
    "BE": 1,
    "PAN": 1,
    "JPP": 1,
}
XVI_GROUPS = ["PSD", "PS", "CH", "IL", "BE", "PCP", "L", "CDS-PP", "PAN"]
CIRCLES = 22
XVI = ("XVI", 107, "2024-03-26", "2025-06-02")
XVII = ("XVII", 108, "2025-06-03", None)


def _xvii_seats():
    """[(cadastro_id, group)] for the 230 seats on the extract date, PS's last one being 232."""
    seats, cad = [], 1
    for group, n in KNOWN_SPLIT.items():
        for _ in range(n - (1 if group == "PS" else 0)):
            seats.append((cad, group))
            cad += 1
    return seats


def _rows():
    mandates, memberships = [], []

    def mandate(leg, cad, situation, effective, start, end):
        leg_name, leg_id, *_ = leg
        circle = cad % CIRCLES + 1
        mandates.append((leg_name, cad, leg_id * 10000 + cad, circle, situation, effective, start, end))

    def member(leg, cad, group, start, end):
        memberships.append((leg[0], cad, 1, group, start, end, leg[3] is None and end is None))

    for cad, group in _xvii_seats():
        mandate(XVII, cad, "Efetivo", True, XVII[2], None)
        member(XVII, cad, group, XVII[2], None)
    mandate(XVII, 231, "Efetivo", True, XVII[2], "2025-12-31")
    mandate(XVII, 231, "Renunciou", False, "2026-01-01", None)
    member(XVII, 231, "PS", XVII[2], "2025-12-31")
    mandate(XVII, 232, "Suplente", False, XVII[2], "2025-12-31")
    mandate(XVII, 232, "Efetivo Definitivo", True, "2026-01-01", None)
    member(XVII, 232, "PS", "2026-01-01", None)
    mandate(XVII, 500, "Suplente", False, XVII[2], None)

    xvi_people = list(range(1, 51)) + list(range(300, 480))
    for i, cad in enumerate(xvi_people):
        group = "PS" if cad == 1 else XVI_GROUPS[i % len(XVI_GROUPS)]
        mandate(XVI, cad, "Efetivo", True, XVI[2], XVI[3])
        member(XVI, cad, group, XVI[2], XVI[3])

    people = sorted({m[1] for m in mandates})
    deputies = [
        (cad, f"Nome Completo {cad}", f"Deputado {cad}", "F" if cad % 2 else "M", None, f"Profissão {cad % 5}", "XVII")
        for cad in people
    ]
    coalitions = []
    for leg, name, members in [
        (XVI, "AD", ["PSD", "CDS-PP"]),
        (XVI, "CDU", ["PCP"]),
        (XVI, "FRS", ["PS"]),
        (XVII, "AD", ["PSD", "CDS-PP"]),
        (XVII, "CDU", ["PCP"]),
    ]:
        for group in members:
            coalitions.append(
                (leg[0], name, f"{name}-LISTA", f"Coligação {name}", group, f"Grupo {group}", None, None, None)
            )
    return mandates, memberships, deputies, coalitions


def build_release(root):
    """Write the release folder (Parquet files and manifest.json) and return its path."""
    out = Path(root) / TAG
    out.mkdir(parents=True)
    mandates, memberships, deputies, coalitions = _rows()
    con = duckdb.connect()
    con.execute(
        "create table legislatures (legislature varchar, legislature_id integer, start_date date, "
        "end_date date, extract_date date)"
    )
    con.executemany(
        "insert into legislatures values (?, ?, ?, ?, ?)",
        [(*XVI, XVI[3]), (*XVII, EXTRACT)],
    )
    con.execute(
        "create table mandates (legislature varchar, cadastro_id bigint, deputy_id bigint, circle_id integer, "
        "situation varchar, is_effective boolean, start_date date, end_date date)"
    )
    con.executemany("insert into mandates values (?, ?, ?, ?, ?, ?, ?, ?)", mandates)
    con.execute(
        "create table group_memberships (legislature varchar, cadastro_id bigint, group_id integer, "
        "group_acronym varchar, start_date date, end_date date, is_open boolean)"
    )
    con.executemany("insert into group_memberships values (?, ?, ?, ?, ?, ?, ?)", memberships)
    con.execute(
        "create table deputies (cadastro_id bigint, full_name varchar, parliamentary_name varchar, sex varchar, "
        "birth_date date, profession varchar, biography_legislature varchar)"
    )
    con.executemany("insert into deputies values (?, ?, ?, ?, ?, ?, ?)", deputies)
    con.execute("create table electoral_circles (legislature varchar, circle_id integer, name varchar)")
    con.executemany(
        "insert into electoral_circles values (?, ?, ?)",
        [(leg[0], i, f"Círculo {i}") for leg in (XVI, XVII) for i in range(1, CIRCLES + 1)],
    )
    con.execute("create table parliamentary_groups (legislature varchar, group_acronym varchar, name varchar)")
    con.executemany(
        "insert into parliamentary_groups values (?, ?, ?)",
        [("XVI", g, f"Grupo {g}") for g in XVI_GROUPS] + [("XVII", g, f"Grupo {g}") for g in KNOWN_SPLIT],
    )
    con.execute(
        "create table coalitions (legislature varchar, coalition varchar, ballot_acronym varchar, "
        "coalition_name varchar, group_code varchar, group_name varchar, source_url varchar, "
        "election_url varchar, note varchar)"
    )
    con.executemany("insert into coalitions values (?, ?, ?, ?, ?, ?, ?, ?, ?)", coalitions)
    agenda = agenda_tables()
    for table, (columns, rows) in agenda.items():
        con.execute(f"create table {table} ({columns})")
        con.executemany(f"insert into {table} values ({', '.join('?' * len(rows[0]))})", rows)  # noqa: S608
    marts = {}
    for mart in (
        "legislatures",
        "mandates",
        "group_memberships",
        "deputies",
        "electoral_circles",
        "parliamentary_groups",
        "coalitions",
        *agenda,
    ):
        path = out / f"{mart}.parquet"
        con.execute(f"copy {mart} to '{path}' (format parquet)")
        rows = con.execute(f"select count(*) from {mart}").fetchone()[0]  # noqa: S608
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        marts[mart] = {"rows": rows, "files": {"parquet": {"name": path.name, "sha256": sha}}}
    manifest = {
        "tag": TAG,
        "schema_version": "1.2.0",
        "source_updated": "2026-10-20",
        "data_commit": "0123456789abcdef0123456789abcdef01234567",
        "marts": marts,
    }
    (out / "manifest.json").write_text(json.dumps(manifest))
    return out


def build_site_data(root):
    """Sync the synthetic release into root/data and return that data folder."""
    root = Path(root)
    data_dir = root / "data"
    sync.sync(data_dir, from_dir=build_release(root / "release"))
    return data_dir
