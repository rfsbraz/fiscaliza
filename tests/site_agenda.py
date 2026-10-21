"""Votes, initiatives and interventions for the agenda page, added to the synthetic release in
tests/site_data.py. Ids and made-up titles only.

XVII plenary votes, newest first (the extract date is 2026-10-19, so "this year" is 2026):

- 306 (2026-06-10) approved on the generality of initiative 33; every group in favour, CH absent.
- 304 (2026-05-05) approved, unanimous, no initiative (Voto de pesar 1) and no positions.
- 303 (2026-03-20) rejected; initiatives 33 and 34 voted together. PSD, CDS-PP and 2 PS deputies
  in favour, PS and CH against, IL abstains.
- 302 (2026-01-15) approved unanimously on initiative 32, every group an inferred favour row.
- 301 (2025-12-10) approved, initiative 31.

Vote 305 (2026-05-05) is a committee vote and never counts. Vote 308 (2025-03-01) is in XVI.
Initiatives 33, 34 and 35 were presented in 2026. Interventions: three in 2026 (two on
2026-01-15, one on 2026-02-05) and one on 2025-11-05.
"""

XVII_GROUPS = ["PSD", "CH", "PS", "IL", "L", "PCP", "CDS-PP", "BE", "PAN", "JPP"]


def agenda_tables():
    """{table: (columns, rows)} for the release."""
    votes = [
        # vote_id, legislature, date, body, result, unanimous, description
        (301, "XVII", "2025-12-10", "plenary", "Aprovado", False, None),
        (302, "XVII", "2026-01-15", "plenary", "Aprovado", True, None),
        (303, "XVII", "2026-03-20", "plenary", "Rejeitado", False, None),
        (304, "XVII", "2026-05-05", "plenary", "Aprovado", True, "Voto de pesar 1"),
        (305, "XVII", "2026-05-05", "Comissão de Saúde", "Aprovado", False, None),
        (306, "XVII", "2026-06-10", "plenary", "Aprovado", False, None),
        (308, "XVI", "2025-03-01", "plenary", "Rejeitado", False, None),
    ]
    initiative_votes = [
        # vote_id, initiative_id, initiative_legislature, body, phase
        (301, 31, "XVII", "plenary", "Votação final global"),
        (302, 32, "XVII", "plenary", "Votação final global"),
        (303, 33, "XVII", "plenary", "Votação na generalidade"),
        (303, 34, "XVII", "plenary", "Votação na generalidade"),
        (305, 35, "XVII", "Comissão de Saúde", "Votação na especialidade"),
        (306, 33, "XVII", "plenary", "Votação na generalidade"),
        (308, 36, "XVI", "plenary", "Votação final global"),
    ]
    initiatives = [
        # legislature, initiative_id, number, type_code, type, title, first_event_date
        ("XVII", 31, 31, "J", "Projeto de Lei", "Iniciativa 31", "2025-10-01"),
        ("XVII", 32, 32, "J", "Projeto de Lei", "Iniciativa 32", "2025-11-01"),
        ("XVII", 33, 33, "J", "Projeto de Lei", "Iniciativa 33", "2026-02-01"),
        ("XVII", 34, 34, "R", "Projeto de Resolução", "Iniciativa 34", "2026-02-02"),
        ("XVII", 35, 35, "J", "Projeto de Lei", "Iniciativa 35", "2026-04-01"),
        ("XVI", 36, 36, "J", "Projeto de Lei", "Iniciativa 36", "2025-01-10"),
    ]
    positions = [(302, "XVII", "plenary", g, "favour", None, True) for g in XVII_GROUPS]
    positions += [
        (303, "XVII", "plenary", "PSD", "favour", None, False),
        (303, "XVII", "plenary", "CDS-PP", "favour", None, False),
        (303, "XVII", "plenary", "PS", "favour", 2, False),
        (303, "XVII", "plenary", "PS", "against", None, False),
        (303, "XVII", "plenary", "CH", "against", None, False),
        (303, "XVII", "plenary", "IL", "abstention", None, False),
    ]
    positions += [(306, "XVII", "plenary", g, "favour", None, False) for g in XVII_GROUPS if g != "CH"]
    positions += [(306, "XVII", "plenary", "CH", "absent", None, False)]
    positions += [(308, "XVI", "plenary", "PS", "against", None, False)]
    interventions = [
        # legislature, intervention_id, meeting_date, cadastro_id
        ("XVII", 1, "2026-01-15", 1),
        ("XVII", 2, "2026-01-15", 90),
        ("XVII", 3, "2026-02-05", 150),
        ("XVII", 4, "2025-11-05", 2),
    ]
    return {
        "votes": (
            "vote_id bigint, legislature varchar, date date, body varchar, result varchar, unanimous boolean, "
            "description varchar",
            votes,
        ),
        "initiative_votes": (
            "vote_id bigint, initiative_id bigint, initiative_legislature varchar, body varchar, phase varchar",
            initiative_votes,
        ),
        "initiatives": (
            "legislature varchar, initiative_id bigint, number integer, type_code varchar, type varchar, "
            "title varchar, first_event_date date",
            initiatives,
        ),
        "vote_group_positions": (
            "vote_id bigint, legislature varchar, body varchar, group_code varchar, position varchar, "
            "deputies integer, inferred boolean",
            positions,
        ),
        "interventions": (
            "legislature varchar, intervention_id bigint, meeting_date date, cadastro_id bigint",
            interventions,
        ),
    }
