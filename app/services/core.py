"""Core pages: legislatures, dashboard statistics, deputies list, parties and coalitions
(F01, F02, F03, F21, F31).

Each function takes a DuckDB cursor and returns the exact payload the frontend reads; the
contracts in tests/contracts/endpoints are the spec. Seat counts use the seating rule from
parlamento-aberto (seated_on) on the legislature's reference day: its last day once it has
ended, the AR extract date while it is open.
"""

from app.data import repository

PICTURE_URL = "https://app.parlamento.pt/webutils/getimage.aspx?id={}&type=deputado"
MAX_PER_PAGE = 100
TOP_CIRCLES = 10


SERVICE = "fiscaliza-api"


class NotFound(Exception):
    """The legislature or coalition asked for does not exist."""


def _iso(day):
    return day.isoformat() if day is not None else None


def _legislature(con, name=None):
    leg = repository.legislature(con, name) if name else repository.current_legislature(con)
    if leg is None:
        raise NotFound(f"legislature {name!r} not found" if name else "no legislature in the data")
    return leg


def legislature_designation(name):
    """The name shown for a legislature: "XVII Legislatura", but the first assembly, elected in
    1975 to write the Constitution, is the Assembleia Constituinte (#108, #112)."""
    return "Assembleia Constituinte" if name == "Constituinte" else f"{name} Legislatura"


def _legislature_dict(leg):
    return {
        "id": leg["legislature_id"],
        "numero": leg["legislature"],
        "designacao": legislature_designation(leg["legislature"]),
        "data_inicio": _iso(leg["start_date"]),
        "data_fim": _iso(leg["end_date"]),
        "ativa": leg["is_open"],
    }


def legislaturas(con):
    # intervencoes_publicadas: what the AR has published so far, which the methodology page
    # quotes for the legislature in progress (#113).
    interventions = repository.interventions_by_legislature(con)
    return {
        "legislaturas": [
            {
                **_legislature_dict(leg),
                "total_deputados": leg["people_seated"],
                "intervencoes_publicadas": interventions.get(leg["legislature"], 0),
            }
            for leg in repository.legislatures(con)
        ]
    }


def estatisticas(con, legislatura=None):
    leg = _legislature(con, legislatura)
    groups = repository.seats_by_group(con, leg["legislature"], leg["ref_day"])
    circles = repository.seats_by_circle(con, leg["legislature"], leg["ref_day"])
    seated = sum(g["seats"] for g in groups)
    return {
        "totais": {
            "deputados": seated,
            "deputados_eleitos": repository.people_seated(con, leg["legislature"]),
            "deputados_em_exercicio": seated,
            "seated_deputies": seated,
            "partidos": len(groups),
            "circulos": len(circles),
        },
        "distribuicao_partidos": [
            {
                "id": g["group_acronym"],
                "sigla": g["group_acronym"],
                "nome": g["name"] or g["group_acronym"],
                "deputados": g["seats"],
            }
            for g in groups
        ],
        "distribuicao_circulos": [{"circulo": c["circle"], "deputados": c["seats"]} for c in circles[:TOP_CIRCLES]],
        "legislatura": {**_legislature_dict(leg), "data_referencia": _iso(leg["ref_day"])},
    }


def partidos(con, legislatura=None, active_only=True):
    leg = _legislature(con, legislatura)
    seats = {g["group_acronym"]: g["seats"] for g in repository.seats_by_group(con, leg["legislature"], leg["ref_day"])}
    total = sum(seats.values())
    parties = [
        {
            "id": g["group_acronym"],
            "sigla": g["group_acronym"],
            "nome": g["name"],
            "num_deputados": seats.get(g["group_acronym"], 0),
            "percentagem": round(seats.get(g["group_acronym"], 0) / total * 100, 1) if total else 0,
            "ativo": seats.get(g["group_acronym"], 0) > 0,
        }
        for g in repository.groups(con, leg["legislature"])
    ]
    if active_only:
        parties = [p for p in parties if p["ativo"]]
    parties.sort(key=lambda p: (-p["num_deputados"], p["sigla"]))
    return {
        "partidos": parties,
        "total_deputados": total,
        "legislatura": leg["legislature"],
        "active_only": active_only,
        "total_parties": len(parties),
    }


def _periodo(row):
    end = row["legislature_end"]
    return f"{row['legislature_start'].year}-{end.year}" if end else f"{row['legislature_start'].year}-"


def _deputy(person, career, groups, shown_legislature, current):
    shown = next((c for c in career if c["legislature"] == shown_legislature), career[-1])
    completed = [c for c in career if not c["is_open"]]
    in_current = any(c["legislature"] == current for c in career)
    seated = bool(person["is_seated"])
    status = shown["situation"]
    cad = person["cadastro_id"]
    return {
        "deputado_id": shown["deputy_id"],
        "id": shown["deputy_id"],
        "id_cadastro": cad,
        "nome": person["parliamentary_name"],
        "nome_completo": person["full_name"] or person["parliamentary_name"],
        "profissao": person["profession"],
        "picture_url": PICTURE_URL.format(cad),
        "partido_sigla": shown["group_acronym"],
        "circulo": shown["circle"],
        "legislatura_nome": shown["legislature"],
        "is_seated": seated,
        "mandate_status": status,
        "career_info": {
            "is_currently_active": in_current,
            "is_seated": seated,
            "mandate_status": status,
            "is_multi_term": len(career) > 1,
            "total_mandates": len(career),
            "first_mandate": career[0]["legislature"],
            "latest_mandate": career[-1]["legislature"],
            "latest_completed_mandate": (
                {"legislatura": completed[-1]["legislature"], "periodo": _periodo(completed[-1])} if completed else None
            ),
            "parties_served": groups,
        },
    }


def deputados(con, page=1, per_page=20, search=None, legislatura=None, active_only=True):
    current = _legislature(con)["legislature"]
    if legislatura:
        _legislature(con, legislatura)
    page = max(page, 1)
    per_page = min(max(per_page, 1), MAX_PER_PAGE)
    query = {"legislature": legislatura or None, "current_only": active_only, "search": search or None}
    rows = repository.deputies_page(con, current, limit=per_page, offset=(page - 1) * per_page, **query)
    if rows:
        total, records = rows[0]["total"], rows[0]["records"]
    else:
        total, records = repository.deputies_count(con, current, **query)
    ids = [r["cadastro_id"] for r in rows]
    careers, groups = {}, {}
    for c in repository.careers(con, ids):
        careers.setdefault(c["cadastro_id"], []).append(c)
    for g in repository.groups_served(con, ids):
        groups.setdefault(g["cadastro_id"], []).append(g["group_acronym"])
    shown = legislatura or None
    deputies = [_deputy(r, careers[r["cadastro_id"]], groups.get(r["cadastro_id"], []), shown, current) for r in rows]
    seated_now = repository.seats_by_group(con, current, _legislature(con)["ref_day"])
    return {
        "deputados": deputies,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
            "has_next": page * per_page < total,
            "has_prev": page > 1,
        },
        "filters": {
            "total_deputy_records": int(records),
            "active_deputies_count": repository.people_seated(con, current),
            "seated_deputies_count": sum(g["seats"] for g in seated_now),
            "legislatura": legislatura or None,
            "active_only": active_only,
        },
        "legislatura": legislatura or None,
    }


def latest_run(order, ran):
    """The latest unbroken run of legislatures in ``ran``, given every legislature oldest
    first in ``order``."""
    i = max(order.index(leg) for leg in ran)
    run = []
    while i >= 0 and order[i] in ran:
        run.append(order[i])
        i -= 1
    return run[::-1]


def _coalitions(con, sigla=None):
    """{coalition: summary} from the coalitions seed. A coalition is active when it ran in
    the open legislature; its components are the groups of its latest legislature, largest
    first. Its dates are those of its latest unbroken run of legislatures, because a short
    name can come back decades later (AD in 1979 and in 2024)."""
    order = [leg["legislature"] for leg in reversed(repository.legislatures(con))]
    out = {}
    for row in repository.coalition_rows(con, sigla):
        c = out.setdefault(row["coalition"], {"rows": []})
        c["rows"].append(row)
    for name, c in out.items():
        rows = c["rows"]
        latest = max(r["start_date"] for r in rows)
        last = [r for r in rows if r["start_date"] == latest]
        components = []
        for r in last:
            if r["group_code"] not in [p["sigla"] for p in components]:
                components.append({"sigla": r["group_code"], "nome": r["group_name"] or r["group_code"]})
        seats = {
            g["group_acronym"]: g["seats"]
            for g in repository.seats_by_group(con, last[0]["legislature"], last[0]["ref_day"])
        }
        components.sort(key=lambda p: (-seats.get(p["sigla"], 0), p["sigla"]))
        ativa = any(r["is_open"] for r in rows)
        run_legs = latest_run(order, {r["legislature"] for r in rows})
        run = [r for r in rows if r["legislature"] in run_legs]
        c.update(
            sigla=name,
            nome=sorted(r["coalition_name"] for r in last)[0],
            legislature=last[0]["legislature"],
            ref_day=last[0]["ref_day"],
            ativa=ativa,
            data_formacao=_iso(min(r["start_date"] for r in run)),
            data_dissolucao=None if ativa else _iso(max(r["end_date"] for r in run)),
            components=components,
        )
    return out


def _coalition(con, sigla):
    found = _coalitions(con, sigla).get(sigla)
    if found is None:
        raise NotFound(f"coalition {sigla!r} not found")
    return found


def _coalition_dict(con, c):
    seated = repository.seated_in_groups(con, c["legislature"], c["ref_day"], [p["sigla"] for p in c["components"]])
    return {
        "id": c["sigla"],
        "sigla": c["sigla"],
        "nome": c["nome"],
        "tipo_coligacao": "eleitoral",
        "ativa": c["ativa"],
        "data_formacao": c["data_formacao"],
        "data_dissolucao": c["data_dissolucao"],
        "legislatura": c["legislature"],
        "component_parties": [{"sigla": p["sigla"], "nome": p["nome"]} for p in c["components"]],
        "deputy_count": len(seated),
        # Editorial fields with no source in the release: left empty, the page guards them.
        "espectro_politico": None,
        "observacoes": None,
    }


def coligacoes(con, include_inactive=False):
    found = [_coalition_dict(con, c) for c in _coalitions(con).values() if include_inactive or c["ativa"]]
    found.sort(key=lambda c: c["sigla"])
    return {"coligacoes": found, "total": len(found), "include_inactive": include_inactive}


def coligacao(con, sigla):
    return _coalition_dict(con, _coalition(con, sigla))


def coligacao_deputados(con, sigla, legislatura=None):
    c = _coalition(con, sigla)
    leg = _legislature(con, legislatura) if legislatura else {"legislature": c["legislature"], "ref_day": c["ref_day"]}
    groups = sorted({r["group_code"] for r in c["rows"] if r["legislature"] == leg["legislature"]})
    seated = repository.seated_in_groups(con, leg["legislature"], leg["ref_day"], groups) if groups else []
    return {
        "coligacao": {"sigla": c["sigla"], "nome": c["nome"], "tipo_coligacao": "eleitoral"},
        "deputados": [
            {
                "id": s["cadastro_id"],
                "id_cadastro": s["cadastro_id"],
                "nome": s["parliamentary_name"],
                "nome_completo": s["full_name"],
                "partido_sigla": s["group_acronym"],
                "circulo": s["circle"],
                "picture_url": PICTURE_URL.format(s["cadastro_id"]),
            }
            for s in seated
        ],
        "total_deputados": len(seated),
        "legislatura": leg["legislature"],
    }


def coligacao_partidos(con, sigla):
    c = _coalition(con, sigla)
    first = {}
    for r in c["rows"]:
        first.setdefault(r["group_code"], r["start_date"])
    parties = [
        {"sigla": p["sigla"], "nome": p["nome"], "data_adesao": _iso(first.get(p["sigla"])), "papel_coligacao": None}
        for p in c["components"]
    ]
    return {
        "coligacao": {"sigla": c["sigla"], "nome": c["nome"], "tipo_coligacao": "eleitoral"},
        "partidos": parties,
        "total_partidos": len(parties),
    }


def health(con):
    """The live release: tag, schema version, source_updated, data commit and sync time, as
    text. The footer shows the tag and source_updated on every page."""
    meta = repository.meta(con) or {}
    data = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in meta.items()}
    return {"status": "healthy", "service": SERVICE, "data": data}
