"""Deputy page: header and statistics, interventions and initiatives, interest register
(F04 to F08, F10, F11 without phase, F13, F14).

Each function takes a DuckDB cursor and returns the payload DeputadoDetalhes.jsx reads; the
contracts in tests/contracts/endpoints are the spec. Dropped for good: the invented opposition
context (F09) and the family fields of the interest register (F15). Attendance waits for its
mart, so ``taxa_assiduidade`` is null and the page hides the card.
"""

from app.data import repository
from app.services.core import PICTURE_URL, NotFound, _iso, _legislature, _periodo

MAX_PER_PAGE = 100
MAX_INITIATIVES = 100
# From XVI on the interest register is kept by the Entidade para a Transparência, which has
# not authorised publishing it yet; the AR open data stops at XV.
EPT_FROM = "XVI"
EPT_URL = "https://entidadetransparencia.pt/"
INITIATIVE_URL = "https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID={}"


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


def detalhes(con, cadastro_id):
    person, career = _person(con, cadastro_id)
    current = _legislature(con)
    latest = career[-1]
    leg = latest["legislature"]
    seated = repository.is_seated(con, cadastro_id)
    periods = {p["legislature"]: p for p in repository.seat_periods(con, cadastro_id)}
    names = repository.group_names(con, [c["legislature"] for c in career])
    completed = [c for c in career if not c["is_open"]]

    activity = {a["legislature"]: a for a in repository.deputy_activity_by_legislature(con, cadastro_id)}
    proposed = sum(a["initiatives"] for a in activity.values())
    approved = sum(a["approved"] for a in activity.values())
    interventions = sum(a["interventions"] for a in activity.values())
    here = activity.get(leg, {"initiatives": 0, "interventions": 0})
    compare = repository.legislature_comparison(con, cadastro_id, leg, latest["group_acronym"])
    days = sum(p["days"] for p in periods.values())

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
            "iniciativas_propostas": proposed,
            "iniciativas_aprovadas": approved,
            "taxa_aprovacao": round(approved / proposed * 100, 1) if proposed else 0.0,
            "iniciativas_por_tipo": [
                {"codigo": t["type_code"], "descricao": t["type"] or t["type_code"], "total": t["total"]}
                for t in repository.deputy_initiative_types(con, cadastro_id)
            ],
            "intervencoes_parlamentares": interventions,
            "taxa_assiduidade": None,
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
            # F08, within the latest legislature the person sat in.
            "iniciativas_legislatura": here["initiatives"],
            "intervencoes_legislatura": here["interventions"],
            "media_partido_iniciativas": round(compare["party_initiatives"] or 0, 2),
            "media_partido_intervencoes": round(compare["party_interventions"] or 0, 2),
            "percentil_nacional": round((compare["rank"] or 0) * 100),
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
        "data": _iso(row["first_event_date"]),
        "data_apresentacao": _iso(row["first_event_date"]),
        "autores": row["authors"] or [],
        "is_cross_party": (row["groups"] or 0) > 1,
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
    seat = next((c for c in career if c["legislature"] == name), None)
    compare = repository.legislature_comparison(con, cadastro_id, name, seat["group_acronym"]) if seat else None
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
        # Averages over everyone who held a seat in the legislature, and over the deputy's group.
        "medias_intervencoes": {
            "partido": round(compare["party_interventions"] or 0, 2) if compare else None,
            "parlamento": round(compare["all_interventions"] or 0, 2) if compare else None,
        },
        "iniciativas": [_initiative(r) for r in initiatives],
        "iniciativas_total": initiatives[0]["total"] if initiatives else 0,
    }


def conflitos_interesse(con, cadastro_id):
    person, _ = _person(con, cadastro_id)
    pending = repository.seated_since(con, cadastro_id, EPT_FROM)
    out = {
        "deputado_id": cadastro_id,
        "tem_declaracao": False,
        "ept": {"pendente": bool(pending), "legislaturas": pending, "url": EPT_URL},
    }
    declaration = repository.latest_declaration(con, cadastro_id)
    if declaration is None:
        return out
    items = repository.declaration_items(
        con, declaration["legislature"], declaration["declaration_key"], ["activity", "society"]
    )
    activities = [
        {"entity_name": i["entity"], "function_type": i["description"]} for i in items if i["category"] == "activity"
    ]
    shareholdings = [
        {"entity_name": i["entity"], "share_percentage": i["share"]} for i in items if i["category"] == "society"
    ]
    exclusive = declaration["is_exclusive"]
    out.update(
        tem_declaracao=True,
        full_name=person["full_name"] or person["parliamentary_name"],
        legislatura=declaration["legislature"],
        last_updated=_iso(declaration["version_date"]),
        declaration_url=None,
        is_exclusive=exclusive,
        has_conflict_potential=exclusive is False or bool(activities) or bool(shareholdings),
        professional_activities=activities,
        shareholdings=shareholdings,
        # No sector or legislation matching in the release yet; the page hides the sector status.
        regulated_sector_count=None,
        total_sectors=None,
    )
    return out
