"""Voting analytics for the deputy and party pages (F16, F17, F19, F25 to F29).

Each function takes a DuckDB cursor and returns the payload the frontend reads; the
contracts in tests/contracts/endpoints are the spec. Figures are descriptive counts for one
legislature: no rankings, percentiles or labels. A deputy's position on a plenary vote comes
from deputy_vote_positions (their group's position that day, overridden when the detail
names them); votes where it is unknown are left out and counted.
"""

from collections import defaultdict

from app.data import repository
from app.data.deputy_rows import DeputyRows
from app.services.core import NotFound

POSITIONS = {"favour": "favor", "against": "contra", "abstention": "abstencao", "absent": "ausente"}
RESULTS = {"Aprovado": "aprovada", "Rejeitado": "rejeitada", "Prejudicado": "prejudicada", "Retirado": "retirada"}
INITIATIVE_URL = "https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID={}"
NO_DESCRIPTION = "Votação sem descrição publicada"
CLOSE_MARGIN = 10
MIN_DECIDED = 10
RATE_TYPES = ("J", "R", "D")
ROMAN = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def legislature_name(value):
    """The legislature as the marts name it. The party page sends a number ("17")."""
    if value is None:
        return None
    value = str(value).strip()
    if not value.isdigit():
        return value.upper()
    n, out = int(value), ""
    for size, numeral in ROMAN:
        while n >= size:
            out, n = out + numeral, n - size
    return out


def _rate(part, whole, digits=3):
    return round(part / whole, digits) if whole else None


def _iso(day):
    return day.isoformat() if day is not None else None


def _vote_items(rows, votes):
    """{vote_id: (vote row, {group: position}, [initiatives])} for the given vote ids."""
    return {
        vote_id: (vote, {p["group_code"]: POSITIONS[p["position"]] for p in positions}, initiatives)
        for vote_id, (vote, positions, initiatives) in rows.vote_items(votes).items()
    }


def _initiative_name(initiative):
    name = initiative["type"] or "Iniciativa"
    if initiative["number"] is not None:
        name += f" n.º {initiative['number']}/{initiative['legislature']}"
    return f"{name}: {initiative['title']}" if initiative["title"] else name


def vote_subject(description, initiatives):
    """What a vote was about (#110). The AR leaves most vote descriptions empty, so: the first
    initiative the vote decided (and how many more), else the vote description, else a line
    saying none was published."""
    if initiatives:
        subject = _initiative_name(initiatives[0])
        more = len(initiatives) - 1
        if more:
            subject += f" e mais {more} {'iniciativa' if more == 1 else 'iniciativas'}"
        return subject
    return (description or "").strip() or NO_DESCRIPTION


def _vote_dict(vote, breakdown, initiatives):
    first = initiatives[0] if initiatives else None
    return {
        "vote_id": vote["vote_id"],
        "data": _iso(vote["date"]),
        "objeto": vote_subject(vote["description"], initiatives),
        "iniciativa": {
            "tipo": first["type"],
            "numero": first["number"],
            "legislatura": first["legislature"],
            "titulo": first["title"],
            "fase": first["phase"],
            "url": INITIATIVE_URL.format(first["initiative_id"]),
        }
        if first
        else None,
        "outras_iniciativas": max(len(initiatives) - 1, 0),
        "resultado": RESULTS.get(vote["result"], (vote["result"] or "").lower()),
        "vote_breakdown": breakdown,
    }


def _deputy_legislature(rows, cadastro_id, legislatura):
    career = rows.career(cadastro_id)
    if not career:
        raise NotFound(f"deputado {cadastro_id} não encontrado")
    if legislatura is None:
        return career[-1]
    name = legislature_name(legislatura)
    found = next((c for c in career if c["legislature"] == name), None)
    if found is None:
        raise NotFound(f"o deputado {cadastro_id} não teve lugar na legislatura {name}")
    return found


def deputado_voting_analytics(con, cadastro_id, legislatura=None, rows=None):
    """``rows``: the DeputyRows to answer from; a route passes none and gets the person's."""
    source = rows if rows is not None else DeputyRows(con, [cadastro_id])
    seat = _deputy_legislature(source, cadastro_id, legislatura)
    leg = seat["legislature"]
    votes = source.votes(cadastro_id, leg)
    known = [r for r in votes if r["position"] is not None]

    distribution = {p: 0 for p in POSITIONS.values()}
    days = {}
    for r in known:
        distribution[POSITIONS[r["position"]]] += 1
        day = days.setdefault(r["date"], {"total": 0, "favour": 0, "against": 0, "abstention": 0})
        day["total"] += 1
        if r["position"] != "absent":
            day[r["position"]] += 1

    # No alignment rate with the own group: the AR publishes no per-deputy roll call, so a
    # deputy's position is the group's unless the record names them (#109). The page counts the
    # named different votes instead.
    both_cast = [r for r in known if r["position"] in repository.CAST and r["group_position"] in repository.CAST]
    dissents = [r for r in reversed(both_cast) if r["named"] and r["position"] != r["group_position"]]
    close = source.close_votes(cadastro_id, leg, CLOSE_MARGIN)
    items = _vote_items(source, {r["vote_id"] for r in dissents} | {c["vote_id"] for c in close})

    left_out = len(votes) - len(known)
    return {
        "legislatura": leg,
        "deputy_info": {"cadastro_id": cadastro_id, "party": {"sigla": seat["group_acronym"]}},
        "vote_distribution": distribution,
        "participation_timeline": [
            {
                "date": _iso(day),
                "total_votes": d["total"],
                "participated": d["favour"] + d["against"] + d["abstention"],
                "participation_rate": _rate(d["favour"] + d["against"] + d["abstention"], d["total"]),
                "favor_votes": d["favour"],
                "contra_votes": d["against"],
                "abstention_votes": d["abstention"],
            }
            for day, d in sorted(days.items())
        ],
        "cross_party_collaboration": [
            {
                "party": g["group_acronym"],
                "aligned_votes": g["aligned_votes"],
                "total_votes": g["total_votes"],
                "alignment_rate": _rate(g["aligned_votes"], g["total_votes"]),
            }
            for g in source.group_agreement(cadastro_id, leg)
        ],
        "dissent_votes": [
            {
                **_vote_dict(*items[r["vote_id"]]),
                "voto": POSITIONS[r["position"]],
                "voto_grupo": POSITIONS[r["group_position"]],
            }
            for r in dissents
        ],
        "close_votes": [
            {
                **_vote_dict(*items[c["vote_id"]]),
                "voto": POSITIONS[c["position"]],
                "votos_favor": c["favour"],
                "votos_contra": c["against"],
                "abstencoes": c["abstention"],
            }
            for c in close
        ],
        "data_sources": {
            "votes_counted": len(known),
            "votes_left_out": left_out,
            "close_margin": CLOSE_MARGIN,
            "note": (
                f"{left_out} votações em plenário ficaram de fora: sem detalhe publicado, ou com o grupo "
                "dividido sem os nomes dos deputados."
                if left_out
                else None
            ),
        },
    }


def _group(con, sigla, legislatura):
    leg = legislature_name(legislatura) if legislatura else core_current(con)
    found = repository.group(con, leg, sigla)
    if found is None:
        raise NotFound(f"grupo {sigla!r} não encontrado na legislatura {leg}")
    return leg, found


def core_current(con):
    current = repository.current_legislature(con)
    if current is None:
        raise NotFound("não há nenhuma legislatura nos dados")
    return current["legislature"]


def _type_order(row):
    code = row["type_code"]
    return (RATE_TYPES.index(code) if code in RATE_TYPES else len(RATE_TYPES), code)


def partido_voting_analytics(con, sigla, legislatura=None):
    leg, group = _group(con, sigla, legislatura)
    is_open = repository.legislature(con, leg)["is_open"]

    months = defaultdict(
        lambda: {"total_votes": 0, "favor_votes": 0, "against_votes": 0, "abstention_votes": 0, "initiatives": 0}
    )
    for m in repository.group_monthly_votes(con, leg, sigla):
        months[m["month"]].update(
            total_votes=m["total"],
            favor_votes=m["favour"],
            against_votes=m["against"],
            abstention_votes=m["abstention"],
        )
    for m in repository.group_monthly_initiatives(con, leg, sigla):
        months[m["month"]]["initiatives"] = m["initiatives"]

    outcomes = []
    for t in sorted(repository.group_initiative_outcomes(con, leg, sigla), key=_type_order):
        decided = t["approved"] + t["rejected"]
        rated = t["type_code"] in RATE_TYPES and decided >= MIN_DECIDED
        outcomes.append(
            {
                "type_code": t["type_code"],
                "tipo": t["type"],
                "initiated": t["initiated"],
                "approved": t["approved"],
                "partly_approved": t["partly_approved"],
                "rejected": t["rejected"],
                "undecided": t["initiated"] - decided,
                "approval_rate": _rate(t["approved"], decided) if rated else None,
            }
        )

    activity = repository.group_activity(con, leg, sigla)
    return {
        "legislatura": leg,
        "party_info": {"sigla": group["group_acronym"], "nome": group["name"] or group["group_acronym"]},
        "temporal_behavior": [{"date": m, **v} for m, v in sorted(months.items())],
        "legislative_effectiveness": {
            "by_type": outcomes,
            "min_decided": MIN_DECIDED,
            "note": (
                "Taxa de aprovação sobre as iniciativas votadas: aprovadas numa votação final, ou rejeitadas "
                "numa votação final ou na generalidade. Só para projetos de lei, de resolução e de "
                f"deliberação com pelo menos {MIN_DECIDED} iniciativas votadas. Sem desfecho conta as "
                "caducadas, retiradas e ainda por votar, que os dados não distinguem. Uma iniciativa "
                "conjunta conta para cada grupo que a assina."
            ),
        },
        "cohesion_by_theme": [
            {
                "type_code": c["type_code"],
                "tema": c["type"],
                "total_votes": c["total_votes"],
                # A count for this group alone: the record only names deputies who vote
                # differently, and small groups have few to name, so no rate to compare (#109).
                "cohesive_votes": c["cohesive_votes"],
            }
            for c in repository.group_cohesion_by_type(con, leg, sigla)
        ],
        "coalition_patterns": [
            {
                "party": g["group_acronym"],
                "aligned_votes": g["aligned_votes"],
                "total_votes": g["total_votes"],
                "alignment_rate": _rate(g["aligned_votes"], g["total_votes"]),
            }
            for g in repository.group_agreement(con, leg, sigla)
        ],
        "participation_metrics": {
            "total_initiatives": activity["initiatives"],
            "total_interventions": activity["interventions"],
            "total_votes_participated": activity["votes"],
            "interventions_note": (
                "A legislatura está em curso e a fonte da Assembleia ainda publica poucas intervenções."
                if is_open
                else None
            ),
        },
    }
