"""Votes, initiatives and interventions for the synthetic release in tests/site_data.py.

Ids and made-up names only. XVII seats (see site_data): PSD 1 to 89, CH 90 to 149, PS 150 to
206 plus 231 (until 2025-12-31) or 232 (from 2026-01-01), IL 207 to 215, L 216 to 221, PCP 222
to 224, CDS-PP 225 and 226, BE 227, PAN 228, JPP 229.

XVII plenary votes:

- 1 (2025-07-10) unanimous, no positions published, so every group gets an inferred favour row.
- 2 (2025-09-10) PSD and CDS-PP favour, IL, PAN and JPP abstain, the rest against. Person 2
  (PSD) is named against. Rejected 90 to 129.
- 3 (2025-11-20) PSD, CDS-PP and IL favour, CH abstains, PS against except 3 unnamed PS deputies
  in favour, the rest against. PS deputies have no known position on it.
- 4 (2026-02-10) PS and CH against, the rest favour, person 2 named as abstaining. Rejected
  111 to 118, a close vote.
- 5 (2026-03-05) not unanimous and no detail: no positions at all.
- 6 (2026-04-10) PSD and CDS-PP abstain, the rest against. Person 1 is named absent.
- 8 (2026-05-04) PSD and CH favour, PS against, the rest abstain. Person 1 is named against.

Vote 7 is a committee vote and never counts. XVI: vote 9 (2024-06-03) PS favour, PSD against,
the rest abstain; votes 20 to 34 decide PSD's XVI initiatives and have no detail.
"""

XVII_GROUPS = ["PSD", "CH", "PS", "IL", "L", "PCP", "CDS-PP", "BE", "PAN", "JPP"]
XVI_GROUPS = ["PSD", "PS", "CH", "IL", "BE", "PCP", "L", "CDS-PP", "PAN"]


def _positions(vote_id, legislature, groups, default, **by_group):
    return [
        (vote_id, legislature, "plenary", g, by_group.get(g.replace("-", "_"), default), None, False) for g in groups
    ]


def _votes():
    votes = [
        # vote_id, legislature, date, body, result, unanimous, description
        (1, "XVII", "2025-07-10", "plenary", "Aprovado", True, "Votação 1"),
        (2, "XVII", "2025-09-10", "plenary", "Rejeitado", False, "Votação 2"),
        (3, "XVII", "2025-11-20", "plenary", "Aprovado", False, "Votação 3"),
        (4, "XVII", "2026-02-10", "plenary", "Rejeitado", False, "Votação 4"),
        (5, "XVII", "2026-03-05", "plenary", "Aprovado", False, "Votação 5"),
        (6, "XVII", "2026-04-10", "plenary", "Rejeitado", False, "Votação 6"),
        (7, "XVII", "2026-04-20", "Comissão de Saúde", "Aprovado", False, "Votação 7"),
        (8, "XVII", "2026-05-04", "plenary", "Aprovado", False, "Votação 8"),
        (9, "XVI", "2024-06-03", "plenary", "Aprovado", False, "Votação 9"),
    ]
    positions = [(1, "XVII", "plenary", g, "favour", None, True) for g in XVII_GROUPS]
    positions += _positions(
        2,
        "XVII",
        XVII_GROUPS,
        "against",
        PSD="favour",
        CDS_PP="favour",
        IL="abstention",
        PAN="abstention",
        JPP="abstention",
    )
    positions += _positions(
        3, "XVII", XVII_GROUPS, "against", PSD="favour", CDS_PP="favour", IL="favour", CH="abstention"
    )
    positions.append((3, "XVII", "plenary", "PS", "favour", 3, False))
    positions += _positions(4, "XVII", XVII_GROUPS, "favour", PS="against", CH="against")
    positions += _positions(6, "XVII", XVII_GROUPS, "against", PSD="abstention", CDS_PP="abstention")
    positions += _positions(7, "XVII", ["PSD", "PS"], "favour")
    positions += _positions(8, "XVII", XVII_GROUPS, "abstention", PSD="favour", CH="favour", PS="against")
    positions += _positions(9, "XVI", XVI_GROUPS, "abstention", PS="favour", PSD="against")
    dissents = [
        # vote_id, legislature, body, position, name, group_code, cadastro_id, candidates
        (2, "XVII", "plenary", "against", "Deputado 2", "PSD", 2, 1),
        (4, "XVII", "plenary", "abstention", "Deputado 2", "PSD", 2, 1),
        (6, "XVII", "plenary", "absent", "Deputado 1", "PSD", 1, 1),
        (8, "XVII", "plenary", "against", "Deputado 1", "PSD", 1, 1),
    ]
    return votes, positions, dissents


def _initiatives():
    """XVII: votes 2, 4, 6 and 8 decide projetos de lei by PSD, votes 1 and 3 projetos de
    resolução by PS deputies. XVI: PSD has 12 projetos de lei (7 approved, 3 rejected on the
    generality, 1 never voted, 1 voted point by point with one point approved and one
    rejected), one of them with PS, and 2 projetos de resolução (one approved, one rejected)."""
    initiatives, authors, links, votes = [], [], [], []

    def initiative(leg, ini, type_code, day, authored_by):
        kind = {"J": "Projeto de Lei", "R": "Projeto de Resolução"}[type_code]
        initiatives.append((leg, ini, ini, type_code, kind, f"Iniciativa {ini}", day))
        for author in authored_by:
            if isinstance(author, str):
                authors.append((leg, ini, "group", None, author, author))
            else:
                cad, group = author
                authors.append((leg, ini, "deputy", cad, group, f"Deputado {cad}"))

    for ini, vote, phase in [
        (2, 2, "Votação na generalidade"),
        (4, 4, "Votação final global"),
        (6, 6, "Votação na generalidade"),
        (8, 8, "Votação final global"),
    ]:
        initiative("XVII", ini, "J", "2025-07-01", ["PSD", (1, "PSD")])
        links.append((vote, ini, "XVII", "plenary", phase))
    for ini, vote in [(1, 1), (3, 3)]:
        initiative("XVII", ini, "R", "2025-07-01", [(150, "PS")])
        links.append((vote, ini, "XVII", "plenary", "Votação Deliberação"))

    vote_id = 20
    for n in range(12):
        ini = 100 + n
        initiative("XVI", ini, "J", "2024-05-01", ["PSD", "PS"] if n == 0 else ["PSD"])
        if n < 7:
            outcomes = [("Votação final global", "Aprovado")]
        elif n < 10:
            outcomes = [("Votação na generalidade", "Rejeitado")]
        elif n == 10:
            outcomes = []
        else:
            outcomes = [("Votação final global", "Aprovado"), ("Votação final global", "Rejeitado")]
        for phase, result in outcomes:
            links.append((vote_id, ini, "XVI", "plenary", phase))
            votes.append((vote_id, "XVI", "2025-01-15", "plenary", result, False, f"Votação {vote_id}"))
            vote_id += 1
    for ini, phase, result in [(120, "Votação final", "Aprovado"), (121, "Votação Deliberação", "Rejeitado")]:
        initiative("XVI", ini, "R", "2024-05-01", ["PSD"])
        links.append((vote_id, ini, "XVI", "plenary", phase))
        votes.append((vote_id, "XVI", "2025-01-16", "plenary", result, False, f"Votação {vote_id}"))
        vote_id += 1
    return initiatives, authors, links, votes


def _interventions():
    rows = [
        ("XVII", 1, "2026-09-16", 1, "PSD"),
        ("XVII", 2, "2026-09-17", 2, "PSD"),
        ("XVII", 3, "2026-09-17", 150, "PS"),
    ]
    return [(leg, 5000 + i, day, "Intervenção", "deputy", cad, group) for leg, i, day, cad, group in rows]


def voting_tables():
    """{table: (columns, rows)} for the votes, initiatives and interventions marts."""
    votes, positions, dissents = _votes()
    initiatives, authors, links, decided = _initiatives()
    return {
        "votes": (
            "vote_id bigint, legislature varchar, date date, body varchar, result varchar, unanimous boolean, "
            "description varchar",
            votes + decided,
        ),
        "vote_group_positions": (
            "vote_id bigint, legislature varchar, body varchar, group_code varchar, position varchar, "
            "deputies integer, inferred boolean",
            positions,
        ),
        "vote_deputy_dissents": (
            "vote_id bigint, legislature varchar, body varchar, position varchar, name varchar, "
            "group_code varchar, cadastro_id bigint, candidates integer",
            dissents,
        ),
        "initiatives": (
            "legislature varchar, initiative_id bigint, number integer, type_code varchar, type varchar, "
            "title varchar, first_event_date date",
            initiatives,
        ),
        "initiative_authors": (
            "legislature varchar, initiative_id bigint, author_type varchar, cadastro_id bigint, "
            "group_code varchar, name varchar",
            authors,
        ),
        "initiative_votes": (
            "vote_id bigint, initiative_id bigint, initiative_legislature varchar, body varchar, phase varchar",
            links,
        ),
        "interventions": (
            "legislature varchar, intervention_id bigint, meeting_date date, intervention_type varchar, "
            "speaker_kind varchar, cadastro_id bigint, group_acronym varchar",
            _interventions(),
        ),
    }
