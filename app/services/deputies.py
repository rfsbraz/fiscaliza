"""Deputy page: header and statistics, interventions and initiatives, interest register
(F04 to F08, F10, F11 without phase, F13, F14).

Each function takes a DuckDB cursor and returns the payload DeputadoDetalhes.jsx reads; the
contracts in tests/contracts/endpoints are the spec. Dropped for good: the invented opposition
context (F09) and the family fields of the interest register (F15). Attendance (F12) is in
app.services.attendance; the card here reads its latest rate (``estatisticas.assiduidade``).
"""

from datetime import date

from app.data import repository
from app.services.core import PICTURE_URL, NotFound, _iso, _legislature, _periodo

MAX_PER_PAGE = 100
MAX_INITIATIVES = 100
# From XVI on the interest register is kept by the Entidade para a Transparência, which has
# not authorised publishing it yet; the AR open data stops at XV.
EPT_FROM = "XVI"
EPT_URL = "https://entidadetransparencia.pt/"
# The person's interest register on the AR site.
AR_INTERESTS_URL = "https://www.parlamento.pt/DeputadoGP/Paginas/RegistoInteressesInfo.aspx?bid={}"
# Lei n.º 52/2019 came into force on the first day of the XIV Legislature (art. 26.º), and its
# declarations apply to whoever starts, renews or ends functions from then on (art. 25.º, n.º 2).
# Its deadline is 60 days from the start of functions (art. 13.º, n.º 1).
LAW_52_2019_IN_FORCE = date(2019, 10, 25)
INITIATIVE_URL = "https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID={}"
# An approval rate needs at least this many decided initiatives (passed or failed).
MIN_DECIDED = 10
# A group average needs at least this many other people in the comparison population.
MIN_PEERS = 5
SMALL_GROUP = "Grupo demasiado pequeno para comparação"
SHORT_MANDATE = "Mandato curto nesta legislatura; sem comparação"
NO_CLOSED_LEGISLATURE = "Sem legislatura concluída para comparar intervenções"
OPEN_LEGISLATURE = "A {} Legislatura ainda está em curso; sem comparação de intervenções"


def _person(con, cadastro_id):
    """The person and their seats, oldest legislature first. Only people who held a seat have
    a page, the same as in the deputies list."""
    person = repository.deputy(con, cadastro_id)
    career = repository.careers(con, [cadastro_id]) if person else []
    if not career:
        raise NotFound(f"deputy {cadastro_id} not found")
    return person, career


def _experience(mandates):
    if mandates >= 4:
        return "Veterano"
    if mandates >= 2:
        return "Experiente"
    return "Novato"


def _approval(row):
    """One type of projeto in one legislature. The rate counts decided initiatives only: passed
    (fully or on some points) or failed. The rest (lapsed, withdrawn or not voted yet) are in
    ``sem_votacao`` and stay out of the rate."""
    decided = row["approved"] + row["rejected"]
    return {
        "codigo": row["type_code"],
        "descricao": row["type"] or row["type_code"],
        "aprovadas": row["approved"],
        "aprovadas_parcialmente": row["partly_approved"],
        "rejeitadas": row["rejected"],
        "votadas": decided,
        "taxa_aprovacao": round(row["approved"] / decided * 100, 1) if decided >= MIN_DECIDED else None,
        "sem_votacao": row["total"] - decided,
    }


def _signing(row):
    return {
        "grupo_parlamentar": row["grupo_parlamentar"] if row else 0,
        "subscricao_restrita": row["subscricao_restrita"] if row else 0,
        "outros_grupos": row["outros_grupos"] if row else 0,
    }


def _initiative_record(con, cadastro_id, career):
    """Per legislature, newest first: how the person's projetos were signed and how they ended."""
    open_legs = {c["legislature"]: c["is_open"] for c in career}
    outcomes, signing = {}, {r["legislature"]: r for r in repository.deputy_signing(con, cadastro_id)}
    for row in repository.deputy_outcomes(con, cadastro_id):
        outcomes.setdefault(row["legislature"], []).append(_approval(row))
    return [
        {
            "legislatura": leg,
            "aberta": open_legs.get(leg, False),
            "assinatura": _signing(signing.get(leg)),
            "aprovacao": rows,
        }
        for leg, rows in reversed(outcomes.items())
    ]


def _comparison(con, cadastro_id, legislature, measure):
    """The person against the people of their group seated at least half of ``legislature``, per
    seat-year. No average when the person sat less than that or has fewer than MIN_PEERS others."""
    row = repository.group_comparison(con, cadastro_id, legislature, measure) if legislature else None
    out = {
        "legislatura": legislature,
        "grupo": row["group_acronym"] if row else None,
        "deputado_por_ano": round(row["per_year"], 2) if row and row["per_year"] is not None else None,
        "media_grupo_por_ano": None,
        "pares": row["peers"] if row else 0,
        "nota": None,
    }
    if row is None:
        return out
    if not row["eligible"]:
        out["nota"] = SHORT_MANDATE
    elif row["peers"] < MIN_PEERS:
        out["nota"] = SMALL_GROUP
    else:
        out["media_grupo_por_ano"] = round(row["group_per_year"], 2)
    return out


def _interventions_comparison(con, cadastro_id, legislature, is_open):
    """Interventions are published late for an open legislature, so there is no comparison then."""
    if is_open:
        out = _comparison(con, cadastro_id, None, "interventions")
        out.update(legislatura=legislature, nota=OPEN_LEGISLATURE.format(legislature))
        return out
    return _comparison(con, cadastro_id, legislature, "interventions")


def detalhes(con, cadastro_id):
    from app.services import attendance

    person, career = _person(con, cadastro_id)
    current = _legislature(con)
    latest = career[-1]
    leg = latest["legislature"]
    seated = repository.is_seated(con, cadastro_id)
    periods = {p["legislature"]: p for p in repository.seat_periods(con, cadastro_id)}
    names = repository.group_names(con, [c["legislature"] for c in career])
    completed = [c for c in career if not c["is_open"]]

    activity = {a["legislature"]: a for a in repository.deputy_activity_by_legislature(con, cadastro_id)}
    interventions = sum(a["interventions"] for a in activity.values())
    days = sum(p["days"] for p in periods.values())
    interventions_comparison = _comparison(
        con, cadastro_id, completed[-1]["legislature"] if completed else None, "interventions"
    )
    if not completed:
        interventions_comparison["nota"] = NO_CLOSED_LEGISLATURE

    group = latest["group_acronym"]
    return {
        "id_cadastro": cadastro_id,
        "deputado_id": latest["deputy_id"],
        "nome": person["parliamentary_name"],
        "nome_completo": person["full_name"] or person["parliamentary_name"],
        "sexo": person["sex"],
        "data_nascimento": _iso(person["birth_date"]),
        "profissao": person["profession"],
        "picture_url": PICTURE_URL.format(cadastro_id),
        "partido": {"id": group, "sigla": group, "nome": names.get((leg, group)) or group} if group else None,
        "circulo": latest["circle"],
        "legislatura": {"numero": leg, "designacao": f"{leg} Legislatura", "ativa": latest["is_open"]},
        "legislatura_numero": leg,
        "mandato": {
            "inicio": _iso(periods[leg]["seat_start"]) if leg in periods else _iso(latest["legislature_start"]),
            "fim": _iso(periods[leg]["seat_end"]) if leg in periods else _iso(latest["legislature_end"]),
            "partido_sigla": group,
            "circulo_eleitoral": latest["circle"],
        },
        "is_seated": seated,
        "mandate_status": latest["situation"],
        "career_info": {
            "is_currently_active": seated,
            "is_seated": seated,
            "mandate_status": latest["situation"],
            "latest_completed_mandate": (
                {"legislatura": completed[-1]["legislature"], "periodo": _periodo(completed[-1])}
                if completed and not seated
                else None
            ),
        },
        "estatisticas": {
            "iniciativas_por_tipo": [
                {"codigo": t["type_code"], "descricao": t["type"] or t["type_code"], "total": t["total"]}
                for t in repository.deputy_initiative_types(con, cadastro_id)
            ],
            "intervencoes_parlamentares": interventions,
            "assiduidade": attendance.latest_rate(con, cadastro_id, career),
            "tempo_servico_anos": round(days / 365.25, 1),
            "nivel_experiencia": _experience(len(career)),
            "total_mandatos": len(career),
            "legislaturas_servidas": ", ".join(c["legislature"] for c in career),
            "evolucao_legislaturas": [
                {
                    "legislatura": c["legislature"],
                    "iniciativas": activity.get(c["legislature"], {}).get("initiatives", 0),
                    "intervencoes": activity.get(c["legislature"], {}).get("interventions", 0),
                }
                for c in reversed(career)
            ],
            # F06 and F07: per legislature and type, never a career total or a ranking.
            "iniciativas_legislaturas": _initiative_record(con, cadastro_id, career),
            # F08: within the group only. Initiatives on restricted lists in the latest
            # legislature; interventions in the latest closed one.
            "comparacao": {
                "iniciativas_subscricao_restrita": _comparison(con, cadastro_id, leg, "restricted_initiatives"),
                "intervencoes": interventions_comparison,
            },
        },
        "mandatos_historico": [
            {
                "deputado_id": c["deputy_id"],
                "legislatura_numero": c["legislature"],
                "legislatura_nome": f"{c['legislature']} Legislatura",
                "mandato_inicio": _iso(periods[c["legislature"]]["seat_start"])
                if c["legislature"] in periods
                else None,
                "mandato_fim": _iso(periods[c["legislature"]]["seat_end"]) if c["legislature"] in periods else None,
                "circulo": c["circle"],
                "partido_sigla": c["group_acronym"],
                "partido_nome": names.get((c["legislature"], c["group_acronym"])),
                "is_current": c["legislature"] == current["legislature"],
            }
            for c in reversed(career)
        ],
    }


def _pages(pages):
    return "-".join(pages[:1] + pages[-1:]) if pages and len(pages) > 1 else (pages[0] if pages else None)


def _intervention(row):
    return {
        "id": row["intervention_id"],
        "tipo": row["intervention_type"],
        "qualidade": row["speaker_role"],
        "sessao_numero": row["session_number"],
        "data": _iso(row["meeting_date"]),
        "assunto": row["debate"],
        "resumo": row["abstract"],
        "sumario": row["summary"],
        "fase_sessao": row["session_phase"],
        "publicacao": {
            "pub_tipo": row["publication_type"],
            "pub_data": _iso(row["publication_date"]),
            "pub_numero": row["publication_number"],
            "paginas": _pages(row["pages"]),
            "url_diario": row["diary_url"],
        },
        # The release has no video; the page guards these.
        "url_video": None,
        "thumbnail_url": None,
        "duracao_video": None,
    }


def _initiative(row):
    return {
        "id": row["initiative_id"],
        "numero": row["number"],
        "titulo": row["title"],
        "tipo": row["type_code"],
        "tipo_descricao": row["type"],
        "estado": row["result"],
        "resultado": row["result"],
        "aprovada": row["result"] == "Aprovado",
        "aprovada_parcialmente": row["partly_approved"],
        "data": _iso(row["first_event_date"]),
        "data_apresentacao": _iso(row["first_event_date"]),
        "autores": row["authors"] or [],
        "subscricao": row["signing"],
        "subscritores": row["signatories"],
        "urls": {"documento": row["text_url"], "oficial": INITIATIVE_URL.format(row["initiative_id"])},
    }


def _interventions_note(con, leg):
    """For an open legislature the AR publishes interventions late, so the list is incomplete."""
    if not leg["is_open"]:
        return None
    published = repository.legislature_interventions(con, leg["legislature"])
    return (
        f"A {leg['legislature']} Legislatura ainda está em curso e os dados abertos do Parlamento só têm, "
        f"por agora, {published} intervenções publicadas. Esta lista está incompleta."
    )


def atividades(con, cadastro_id, legislatura=None, tipo=None, ordem="newest", page=1, per_page=50):
    person, career = _person(con, cadastro_id)
    leg = _legislature(con, legislatura or career[-1]["legislature"])
    name = leg["legislature"]
    page = max(page, 1)
    per_page = min(max(per_page, 1), MAX_PER_PAGE)
    served = any(c["legislature"] == name for c in career)
    rows = repository.interventions_page(
        con, cadastro_id, name, kind=tipo, order=ordem, limit=per_page, offset=(page - 1) * per_page
    )
    total = rows[0]["total"] if rows else repository.interventions_count(con, cadastro_id, name, kind=tipo)
    initiatives = repository.deputy_initiatives_in(con, cadastro_id, name, limit=MAX_INITIATIVES)
    signing = repository.deputy_signing(con, cadastro_id, name)
    return {
        "deputado": {
            "id_cadastro": cadastro_id,
            "nome": person["parliamentary_name"],
            "served_in_legislature": served,
        },
        "legislatura": {"numero": name, "designacao": f"{name} Legislatura"},
        "intervencoes": [_intervention(r) for r in rows],
        "intervention_metadata": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
        "nota_intervencoes": _interventions_note(con, leg) if served else None,
        "comparacao_intervencoes": _interventions_comparison(con, cadastro_id, name, leg["is_open"])
        if served
        else None,
        "assinatura": _signing(signing[0] if signing else None),
        "aprovacao": [_approval(r) for r in repository.deputy_outcomes(con, cadastro_id, name)],
        "iniciativas": [_initiative(r) for r in initiatives],
        "iniciativas_total": initiatives[0]["total"] if initiatives else 0,
    }


def missing_declaration(cadastro_id, legislature, legislature_start, coverage_start):
    """What the page needs when the AR open data has no declaration for the person. A record
    missing from the open data is not evidence that a declaration was not submitted, so the page
    never says it was. ``legislature`` is the latest the person held a seat in; before the first
    legislature with open data declarations the data does not cover the period at all. The legal
    deadline is shown only for mandates under Lei n.º 52/2019."""
    return {
        "legislatura": legislature,
        "antes_da_cobertura": coverage_start is None or legislature_start < coverage_start,
        "lei_52_2019": legislature_start >= LAW_52_2019_IN_FORCE,
        "url_parlamento": AR_INTERESTS_URL.format(cadastro_id),
        "url_ept": EPT_URL,
    }


def conflitos_interesse(con, cadastro_id):
    person, career = _person(con, cadastro_id)
    pending = repository.seated_since(con, cadastro_id, EPT_FROM)
    coverage = repository.declaration_coverage(con)
    out = {
        "deputado_id": cadastro_id,
        "tem_declaracao": False,
        "ept": {"pendente": bool(pending), "legislaturas": pending, "url": EPT_URL},
        # How few of the seated deputies have a declaration in the AR open data.
        "cobertura": {
            "de": coverage["first_legislature"],
            "ate": coverage["last_legislature"],
            "com_declaracao": coverage["declared"],
            "total": coverage["seated"],
        }
        if coverage and coverage["seated"]
        else None,
    }
    declaration = repository.latest_declaration(con, cadastro_id)
    if declaration is None:
        latest = career[-1]
        out["sem_declaracao"] = missing_declaration(
            cadastro_id,
            latest["legislature"],
            latest["legislature_start"],
            coverage["first_start"] if coverage else None,
        )
        return out
    items = repository.declaration_items(
        con, declaration["legislature"], declaration["declaration_key"], ["activity", "society"]
    )
    # Only fields the release publishes, as published. Dates stay as written in the declaration
    # (some give only a year); the period is what tells two terms in the same post apart.
    activities = [
        {
            "function_type": i["description"],
            "entity_name": i["entity"],
            "location": i["location"],
            "start_date": i["start_date_raw"],
            "end_date": i["end_date_raw"],
        }
        for i in items
        if i["category"] == "activity"
    ]
    shareholdings = [
        {"entity_name": i["entity"], "share_percentage": i["share"], "location": i["location"]}
        for i in items
        if i["category"] == "society"
    ]
    flags = repository.declaration_flags(con, declaration["legislature"], declaration["declaration_key"])
    out.update(
        tem_declaracao=True,
        full_name=person["full_name"] or person["parliamentary_name"],
        legislatura=declaration["legislature"],
        last_updated=_iso(declaration["version_date"]),
        declaration_url=None,
        # As published; null when the declaration does not say.
        is_exclusive=declaration["is_exclusive"],
        # Neutral facts about what was declared. Declaring is a legal duty, not a sign of anything.
        declara_outras_atividades=flags["other_activities"],
        declara_participacoes=flags["shareholdings"],
        professional_activities=activities,
        shareholdings=shareholdings,
    )
    return out
