"""A small synthetic parlamento-aberto release, built into the site's DuckDB file.

Ids and made-up names only, no real people. Two legislatures:

- XVI, closed (2024-03-26 to 2025-06-02): people 1 to 50 and 300 to 479 hold its 230 seats.
- XVII, open, extract date 2026-10-19: people 1 to 229 and 232 hold its 230 seats with the
  known split (KNOWN_SPLIT). Person 231 sat for PS until 2025-12-31 and resigned; person 232 took
  the seat on 2026-01-01. Person 500 is a substitute who never sat.

Person 1 sat for PS in XVI and for PSD in XVII. Coalitions: AD (PSD, CDS-PP) and CDU (PCP)
in both legislatures, and FRS (PS) in XVI only.

Activity (ACTIVITY below): person 1 authored initiatives in both legislatures, one of them with
person 90 (CH), and spoke in both; person 2 (PSD) and person 90 have a little activity in XVII.
The three PCP deputies (222 to 224) sign 12 initiatives as a whole group and 222 and 223 one more
on their own, and person 227 (BE, one seat) one. Person 1 has two interest declarations from XV,
an older and a newer one; person 2 has one that lists only the mandate and leaves exclusivity
blank; person 301 has one from XVI.

Plenary attendance (ATTENDANCE below, the plenary_attendance mart): each list holds whoever had a
seat that day, everyone PR (present) unless listed here.

- XVII: meetings 9000 (2025-10-16, 231 still on the list), 9001 (2026-01-15), 9002 (2026-02-12),
  9003 (2026-03-12), 9004 (2026-04-25, Solene), 9005 (2026-09-17) and 9006 (2026-10-15), the
  last five with 232. Person 1: ME on 9002, FJ on 9003, FI on 9004 (solemn), FA on 9005 (33
  days before source_updated, so pending). Person 2: FA on 9001 (over 60 days, unclassified),
  QV on 9002, PNO on 9003, FI on 9006.
- XVI: meetings 8001 (2024-04-11), 8002 (2024-10-10) and 8003 (2025-03-13). Person 1 (PS): PT,
  CO, FIJ. Person 301: MP, QVJ, PR.
- No lists for any other legislature.

Votes, initiatives and interventions for the agenda page are in tests/site_agenda.py and go into
the same tables (TABLES below). They use their own initiative ids and deputies, so they do not
change the deputy figures; the deputy activity above adds 4 XVII interventions on 3 days of 2026
to the agenda stats.
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


def _activity():
    """Initiatives with their authors and decisive votes, interventions and interest
    declarations. Returns {table: (create sql, rows)}."""
    initiatives = [
        # legislature, initiative_id, number, type_code, type, title, first_event_date, text_url
        ("XVII", 1, 1, "J", "Projeto de Lei", "Iniciativa 1", "2025-07-01", "https://example.org/1.pdf"),
        ("XVII", 2, 2, "R", "Projeto de Resolução", "Iniciativa 2", "2025-08-01", None),
        ("XVII", 3, 3, "J", "Projeto de Lei", "Iniciativa 3", "2025-09-01", None),
        ("XVII", 4, 4, "J", "Projeto de Lei", "Iniciativa 4", "2025-10-01", None),
        ("XVII", 6, 6, "J", "Projeto de Lei", "Iniciativa 6", "2025-11-01", None),
        ("XVI", 5, 5, "J", "Projeto de Lei", "Iniciativa 5", "2024-06-01", None),
        ("XVII", 7, 7, "J", "Projeto de Lei", "Iniciativa 7", "2025-07-15", None),
        ("XVII", 8, 8, "R", "Projeto de Resolução", "Iniciativa 8", "2025-07-20", None),
        ("XVII", 9, 9, "J", "Projeto de Lei", "Iniciativa 9", "2025-07-25", None),
        ("XVII", 10, 10, "J", "Projeto de Lei", "Iniciativa 10", "2025-07-30", None),
        ("XVII", 11, 11, "A", "Apreciação Parlamentar", "Iniciativa 11", "2025-08-05", None),
        *[("XVII", n, n, "J", "Projeto de Lei", f"Iniciativa {n}", "2025-09-15", None) for n in range(30, 43)],
        ("XVII", 43, 43, "J", "Projeto de Lei", "Iniciativa 43", "2025-09-20", None),
    ]
    authors = [
        # legislature, initiative_id, author_type, cadastro_id, group_code, name
        ("XVII", 1, "deputy", 1, "PSD", "Deputado 1"),
        ("XVII", 2, "deputy", 1, "PSD", "Deputado 1"),
        ("XVII", 3, "deputy", 1, "PSD", "Deputado 1"),
        ("XVII", 4, "deputy", 1, "PSD", "Deputado 1"),
        ("XVII", 4, "deputy", 90, "CH", "Deputado 90"),
        ("XVII", 6, "deputy", 2, "PSD", "Deputado 2"),
        ("XVII", 6, "group", None, "PSD", "PSD"),
        ("XVI", 5, "deputy", 1, "PS", "Deputado 1"),
        *[("XVII", n, "deputy", 1, "PSD", "Deputado 1") for n in (7, 8, 9, 10, 11)],
        # 30 to 41: the whole PCP group (3 seats); 42: two of its three deputies.
        *[("XVII", n, "deputy", cad, "PCP", f"Deputado {cad}") for n in range(30, 42) for cad in (222, 223, 224)],
        *[("XVII", 42, "deputy", cad, "PCP", f"Deputado {cad}") for cad in (222, 223)],
        ("XVII", 43, "deputy", 227, "BE", "Deputado 227"),
    ]
    initiative_votes = [
        # vote_id, initiative_id, initiative_legislature, body, phase
        (101, 1, "XVII", "plenary", "Votação na generalidade"),
        (102, 1, "XVII", "plenary", "Votação final global"),
        (103, 2, "XVII", "plenary", "Votação Deliberação"),
        (104, 4, "XVII", "plenary", "Votação na generalidade"),
        (105, 5, "XVI", "plenary", "Votação final global"),
        (106, 6, "XVII", "Comissão de Saúde", "Votação final global"),
        # 7: point by point on the same day, one point passed and one failed.
        (107, 7, "XVII", "plenary", "Votação final global"),
        (108, 7, "XVII", "plenary", "Votação final global"),
        (109, 8, "XVII", "plenary", "Votação final"),
        (110, 9, "XVII", "plenary", "Votação na generalidade"),
        # 10: failed on the generality, then passed a later final global vote.
        (111, 10, "XVII", "plenary", "Votação na generalidade"),
        (112, 10, "XVII", "plenary", "Votação final global"),
        (113, 11, "XVII", "plenary", "Votação final global"),
        *[(200 + n, n, "XVII", "plenary", "Votação final global") for n in range(30, 43)],
    ]
    votes = [
        # vote_id, legislature, date, body, result (unanimous and description added below)
        (101, "XVII", "2025-07-10", "plenary", "Aprovado"),
        (102, "XVII", "2025-12-05", "plenary", "Aprovado"),
        (103, "XVII", "2025-08-10", "plenary", "Rejeitado"),
        (104, "XVII", "2025-10-10", "plenary", "Aprovado"),
        (105, "XVI", "2024-07-10", "plenary", "Aprovado"),
        (106, "XVII", "2025-11-10", "Comissão de Saúde", "Aprovado"),
        (107, "XVII", "2025-11-20", "plenary", "Aprovado"),
        (108, "XVII", "2025-11-20", "plenary", "Rejeitado"),
        (109, "XVII", "2025-11-21", "plenary", "Aprovado"),
        (110, "XVII", "2025-11-22", "plenary", "Rejeitado"),
        (111, "XVII", "2025-09-10", "plenary", "Rejeitado"),
        (112, "XVII", "2025-11-30", "plenary", "Aprovado"),
        (113, "XVII", "2025-11-23", "plenary", "Aprovado"),
        # PCP: 30 to 36 passed, 37 to 42 failed.
        *[(200 + n, "XVII", "2025-12-01", "plenary", "Aprovado" if n < 37 else "Rejeitado") for n in range(30, 43)],
    ]
    # All before the agenda page's votes (from 2025-12-10), so its recent votes stay its own.
    votes = [(*v, False, None) for v in votes]
    interventions = []
    for i, (leg, cad, day, kind) in enumerate(
        [
            ("XVII", 1, "2026-09-16", "Intervenção"),
            ("XVII", 1, "2026-09-17", "Pedido de esclarecimento"),
            ("XVII", 1, "2026-09-18", "Declaração politica"),
            ("XVII", 90, "2026-09-18", "Intervenção"),
            ("XVI", 1, "2024-04-10", "Intervenção"),
            ("XVI", 1, "2024-05-10", "Intervenção"),
            ("XVI", 1, "2024-06-10", "Pergunta"),
            ("XVI", 1, "2024-07-10", "Intervenção"),
            ("XVI", 1, "2024-08-10", "Interpelação à mesa"),
        ],
        start=1,
    ):
        interventions.append(
            (
                leg,
                1000 + i,
                1,
                day,
                kind,
                "Período da ordem do dia",
                f"Debate {i}",
                f"Sumário {i}",
                None,
                "deputy",
                cad,
                "Deputado",
                "DAR I série",
                i,
                day,
                [str(i), str(i + 1)],
                f"https://example.org/dar/{i}",
            )
        )
    declarations = [
        # legislature, declaration_key, cadastro_id, declaration_id, version_date, is_exclusive, position, source
        ("XV", "XV-10", 1, 10, None, True, "Deputado", "ar_open_data"),
        ("XV", "XV-11", 1, 11, None, False, "Deputado", "ar_open_data"),
        ("XV", "XV-12", 2, 12, None, None, "Deputado", "ar_open_data"),
        ("XVI", "XVI-13", 301, 13, None, True, "Deputado", "ar_open_data"),
    ]
    interests = [
        # legislature, declaration_key, item_number, cadastro_id, category, description, entity, share,
        # location, start_date_raw, end_date_raw
        ("XV", "XV-10", 1, 1, "activity", "Atividade antiga", "Entidade Antiga", None, None, None, None),
        ("XV", "XV-11", 1, 1, "activity", "Consultor", "Empresa Exemplo", None, "Lisboa", "2019-01-01", "2021-06-30"),
        ("XV", "XV-11", 2, 1, "society", "Sócio", "Sociedade Exemplo", "10", "Porto", None, None),
        ("XV", "XV-11", 3, 1, "social_position", "Vogal", "Associação Exemplo", None, None, None, None),
        ("XV", "XV-11", 4, 1, "activity", "Deputado", "Assembleia da República", None, "Lisboa", "2022-03-29", None),
        # The same post again for a later period, and an exact repeat of item 1 as published.
        ("XV", "XV-11", 5, 1, "activity", "Consultor", "Empresa Exemplo", None, "Lisboa", "2021-07-01", None),
        ("XV", "XV-11", 6, 1, "activity", "Consultor", "Empresa Exemplo", None, "Lisboa", "2019-01-01", "2021-06-30"),
        # An older declaration: the whole sentence is in the description, with no entity.
        ("XV", "XV-12", 1, 2, "activity", "Deputada à Assembleia da República", None, None, None, "2011", None),
        ("XVI", "XVI-13", 1, 301, "activity", "Deputado", "Assembleia da República", None, None, None, None),
    ]
    return {
        "initiatives": (
            "legislature varchar, initiative_id bigint, number integer, type_code varchar, type varchar, "
            "title varchar, first_event_date date, text_url varchar",
            initiatives,
        ),
        "initiative_authors": (
            "legislature varchar, initiative_id bigint, author_type varchar, cadastro_id bigint, "
            "group_code varchar, name varchar",
            authors,
        ),
        "initiative_votes": (
            "vote_id bigint, initiative_id bigint, initiative_legislature varchar, body varchar, phase varchar",
            initiative_votes,
        ),
        "votes": (
            "vote_id bigint, legislature varchar, date date, body varchar, result varchar, unanimous boolean, "
            "description varchar",
            votes,
        ),
        "interventions": (
            "legislature varchar, intervention_id bigint, session_number integer, meeting_date date, "
            "intervention_type varchar, session_phase varchar, debate varchar, summary varchar, abstract varchar, "
            "speaker_kind varchar, cadastro_id bigint, speaker_role varchar, publication_type varchar, "
            "publication_number integer, publication_date date, pages varchar[], diary_url varchar",
            interventions,
        ),
        "interest_declarations": (
            "legislature varchar, declaration_key varchar, cadastro_id bigint, declaration_id bigint, "
            "version_date date, is_exclusive boolean, position varchar, source varchar",
            declarations,
        ),
        "interests": (
            "legislature varchar, declaration_key varchar, item_number integer, cadastro_id bigint, "
            "category varchar, description varchar, entity varchar, share varchar, location varchar, "
            "start_date_raw varchar, end_date_raw varchar",
            interests,
        ),
    }


ACTIVITY = _activity()

ATTENDANCE_CATEGORY = {
    "PR": "present",
    "PT": "present",
    "PNO": "other_body_or_mission",
    "CO": "other_body_or_mission",
    "ME": "other_body_or_mission",
    "MP": "other_body_or_mission",
    "FJ": "justified",
    "FIJ": "justified",
    "QVJ": "justified",
    "QV": "missed_quorum_vote",
    "FI": "unjustified",
}
SOURCE_UPDATED = "2026-10-20"
XVII_MEETINGS = [
    # meeting_id, number, session, date, type
    (9000, 10, 1, "2025-10-16", "Ordinária"),
    (9001, 20, 1, "2026-01-15", "Ordinária"),
    (9002, 30, 1, "2026-02-12", "Ordinária"),
    (9003, 40, 1, "2026-03-12", "Extraordinária"),
    (9004, 50, 1, "2026-04-25", "Solene"),
    (9005, 60, 2, "2026-09-17", "Ordinária"),
    (9006, 70, 2, "2026-10-15", "Ordinária"),
]
XVI_MEETINGS = [
    (8001, 5, 1, "2024-04-11", "Ordinária"),
    (8002, 50, 2, "2024-10-10", "Ordinária"),
    (8003, 90, 2, "2025-03-13", "Ordinária"),
]
ATTENDANCE_CODES = {
    (1, 9002): "ME",
    (1, 9003): "FJ",
    (1, 9004): "FI",
    (1, 9005): "FA",
    (2, 9001): "FA",
    (2, 9002): "QV",
    (2, 9003): "PNO",
    (2, 9006): "FI",
    (1, 8001): "PT",
    (1, 8002): "CO",
    (1, 8003): "FIJ",
    (301, 8001): "MP",
    (301, 8002): "QVJ",
}


def _attendance():
    """The plenary_attendance mart for the meetings above, as parlamento-aberto publishes it."""
    from datetime import date

    updated = date.fromisoformat(SOURCE_UPDATED)
    xvii = _xvii_seats()
    xvi = list(range(1, 51)) + list(range(300, 480))
    rows = []

    def add(leg, meeting, seats):
        meeting_id, number, session, day, kind = meeting
        for cad, group in seats:
            code = ATTENDANCE_CODES.get((cad, meeting_id), "PR")
            if code == "FA":
                pending = (updated - date.fromisoformat(day)).days < 60
                category = "pending" if pending else "unclassified"
            else:
                pending, category = False, ATTENDANCE_CATEGORY[code]
            rows.append(
                (
                    leg,
                    meeting_id,
                    number,
                    session,
                    day,
                    kind,
                    kind in ("Solene", "Comemorativa"),
                    cad,
                    f"Deputado {cad}",
                    group,
                    group,
                    code,
                    category,
                    pending,
                    SOURCE_UPDATED,
                )
            )

    for meeting in XVII_MEETINGS:
        last = 231 if meeting[3] < "2026-01-01" else 232
        add("XVII", meeting, [*xvii, (last, "PS")])
    for meeting in XVI_MEETINGS:
        add("XVI", meeting, [(cad, "PS" if cad == 1 else XVI_GROUPS[i % len(XVI_GROUPS)]) for i, cad in enumerate(xvi)])
    return {
        "plenary_attendance": (
            "legislature varchar, meeting_id bigint, meeting_number integer, session_number integer, "
            "meeting_date date, meeting_type varchar, is_ceremonial boolean, cadastro_id bigint, "
            "parliamentary_name varchar, group_code varchar, group_code_raw varchar, code varchar, "
            "category varchar, is_pending boolean, source_updated date",
            rows,
        )
    }


ATTENDANCE = _attendance()


def _tables():
    """ACTIVITY with the agenda page's rows added; a table in both must have the same columns."""
    tables = {**ACTIVITY, **ATTENDANCE}
    for table, (columns, rows) in agenda_tables().items():
        if table in tables:
            assert columns == tables[table][0], f"{table}: agenda columns differ from ACTIVITY"
            rows = tables[table][1] + rows
        tables[table] = (columns, rows)
    return tables


TABLES = _tables()


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
    for table, (columns, rows) in TABLES.items():
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
        *TABLES,
    ):
        path = out / f"{mart}.parquet"
        con.execute(f"copy {mart} to '{path}' (format parquet)")
        rows = con.execute(f"select count(*) from {mart}").fetchone()[0]  # noqa: S608
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        marts[mart] = {"rows": rows, "files": {"parquet": {"name": path.name, "sha256": sha}}}
    manifest = {
        "tag": TAG,
        "schema_version": "1.2.0",
        "source_updated": SOURCE_UPDATED,
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
