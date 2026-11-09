"""One plenary day of decisions for the home page (#264), added to the synthetic release in
tests/site_data.py. Ids and made-up titles only.

2026-10-15 is the last day with plenary votes in the release:

- 401: the Government's proposta de lei 81, rejected on the generality. PSD and CDS-PP in
  favour, IL abstains, the rest against.
- 402: projeto de lei 82 by citizens, approved unanimously in the final global vote. Only the
  inferred favour rows of a unanimous vote, no published positions.
- 403: projeto de resolução 83, approved in the final vote. PS abstains and 1 PS deputy is
  counted in favour, the rest in favour.
- 404: the Government's proposta de lei 84, approved in the final global vote, PCP against.
- 405: a procedural request on projeto de lei 85, never a decision.

Vote ids 401 to 405 and initiative ids 81 to 85 stay clear of the other sets.
"""

DAY = "2026-10-15"
INITIATIVE_COLUMNS = (
    "legislature varchar, initiative_id bigint, number integer, type_code varchar, type varchar, "
    "title varchar, first_event_date date, text_url varchar, author_kind varchar"
)
GROUPS = ["PSD", "CH", "PS", "IL", "L", "PCP", "CDS-PP", "BE", "PAN", "JPP"]


def _row(vote, group, position, deputies=None, inferred=False):
    return (vote, "XVII", "plenary", group, position, deputies, inferred)


def decision_tables():
    """{table: (columns, rows)} for the release."""
    votes = [
        # vote_id, legislature, date, body, result, unanimous, description
        (401, "XVII", DAY, "plenary", "Rejeitado", False, None),
        (402, "XVII", DAY, "plenary", "Aprovado", True, None),
        (403, "XVII", DAY, "plenary", "Aprovado", False, None),
        (404, "XVII", DAY, "plenary", "Aprovado", False, None),
        (405, "XVII", DAY, "plenary", "Aprovado", False, None),
    ]
    links = [
        (401, 81, "XVII", "plenary", "Votação na generalidade"),
        (402, 82, "XVII", "plenary", "Votação final global"),
        (403, 83, "XVII", "plenary", "Votação final"),
        (404, 84, "XVII", "plenary", "Votação final global"),
        (405, 85, "XVII", "plenary", "Requerimento baixa comissão sem votação"),
    ]
    initiatives = [
        # legislature, initiative_id, number, type_code, type, title, first_event_date, text_url, author_kind
        ("XVII", 81, 81, "P", "Proposta de Lei", "Iniciativa 81\n", "2026-09-01", None, "Governo"),
        ("XVII", 82, 82, "J", "Projeto de Lei", "Iniciativa 82", "2026-06-01", None, "Cidadãos"),
        ("XVII", 83, 83, "R", "Projeto de Resolução", "Iniciativa 83", "2026-07-01", None, "Grupos Parlamentares"),
        ("XVII", 84, 84, "P", "Proposta de Lei", "Iniciativa 84", "2026-05-01", None, "Governo"),
        ("XVII", 85, 85, "J", "Projeto de Lei", "Iniciativa 85", "2026-08-01", None, "Grupos Parlamentares"),
    ]
    against_401 = {"PSD": "favour", "CDS-PP": "favour", "IL": "abstention"}
    positions = [_row(401, g, against_401.get(g, "against")) for g in GROUPS]
    positions += [_row(402, g, "favour", inferred=True) for g in GROUPS]
    positions += [_row(403, g, "abstention" if g == "PS" else "favour") for g in GROUPS]
    positions.append(_row(403, "PS", "favour", deputies=1))
    positions += [_row(404, g, "against" if g == "PCP" else "favour") for g in GROUPS]
    return {
        "votes": (
            "vote_id bigint, legislature varchar, date date, body varchar, result varchar, unanimous boolean, "
            "description varchar",
            votes,
        ),
        "vote_group_positions": (
            "vote_id bigint, legislature varchar, body varchar, group_code varchar, position varchar, "
            "deputies integer, inferred boolean",
            positions,
        ),
        "initiatives": (INITIATIVE_COLUMNS, initiatives),
        "initiative_votes": (
            "vote_id bigint, initiative_id bigint, initiative_legislature varchar, body varchar, phase varchar",
            links,
        ),
    }
