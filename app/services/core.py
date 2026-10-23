"""Core pages: legislatures, dashboard statistics, deputies list, parties and coalitions
(F01, F02, F03, F21, F31).

Each function takes a DuckDB cursor and returns the exact payload the frontend reads; the
contracts in tests/contracts/endpoints are the spec. Seat counts use the seating rule from
parlamento-aberto (seated_on) on the legislature's reference day: its last day once it has
ended, the AR extract date while it is open.
"""

import json
import re
import unicodedata

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
        raise NotFound(f"legislatura {name!r} não encontrada" if name else "não há nenhuma legislatura nos dados")
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
        ],
        # Who the AR open data has an interest declaration for, which the methodology page quotes.
        "cobertura_declaracoes": _declaration_coverage(con),
    }


def _declaration_coverage(con):
    coverage = repository.declaration_coverage(con)
    if not coverage or not coverage["seated"]:
        return None
    return {
        "de": coverage["first_legislature"],
        "ate": coverage["last_legislature"],
        "com_declaracao": coverage["declared"],
        "total": coverage["seated"],
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


MANDATE_ENDED = repository.MANDATE_ENDED


def _periodo(row):
    end = row["legislature_end"]
    return f"{row['legislature_start'].year}-{end.year}" if end else f"{row['legislature_start'].year}-"


def _deputy(person, career, groups, shown_legislature, current):
    """``career``: every legislature the person was elected or seated in (repository.elections).
    The mandate counts are of the legislatures they held a seat in."""
    shown = next((c for c in career if c["legislature"] == shown_legislature), career[-1])
    served = [c for c in career if c["seated"]]
    completed = [c for c in served if not c["is_open"]]
    in_current = next((c for c in career if c["legislature"] == current), None)
    # In office: in the current legislature with a mandate that did not end for good. A
    # suspended mandate is still a mandate; a resignation is not.
    active = in_current is not None and in_current["situation"] not in MANDATE_ENDED
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
            "is_currently_active": active,
            "in_current_legislature": in_current is not None,
            # Held a seat in the current legislature at some point (#107: an election without a
            # seat is not a mandate). A suspended mandate that sat counts; one that never sat does not.
            "seated_in_current_legislature": in_current is not None and bool(in_current["seated"]),
            "is_seated": seated,
            "mandate_status": status,
            "is_multi_term": len(served) > 1,
            "total_mandates": len(served),
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
    for c in repository.elections(con, ids):
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


# Coalitions. The seed has one row per legislature, list and group, under a short name that
# comes back over the years (AD in 1979 and in 2024) and covers lists that ran only in one
# autonomous region (AD in the Açores, Madeira Primeiro). A page is one list and run (#111):
# lists that won seats in more than one circle, or in a legislature with no seats per circle
# (Constituinte and I-A), form one page per run of consecutive legislatures; a list that won
# seats only in the Açores or Madeira is a page per election.

REGIONS = ("Açores", "Madeira")


def _slug(value):
    """The path form of a name, as fiscaliza_data.export.slug."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _region(circles):
    """The autonomous region a list won all its seats in, else None."""
    if circles and len(circles) == 1 and next(iter(circles)) in REGIONS:
        return next(iter(circles))
    return None


def coalition_pages(order, lists):
    """The coalition pages for ``lists``, one dict per list in a legislature with coalition,
    legislature, ballot_acronym, circles (the circles where it won seats, None when the release
    has none) and election_year; ``order`` is every legislature oldest first. Each page has id,
    sigla, ambito (the region, None for a national list), legislaturas (oldest first), eleicoes
    and listas ({(legislature, ballot acronym)}).

    A short name with one page keeps it as its id (CDU, PàF). Otherwise each id is the short
    name's path form, then the region unless the name already says it, then the year of the
    page's first election: ad-1979, ad-2024, ad-acores-2025, madeira-primeiro-2022."""
    pages = []
    by_name = {}
    for entry in lists:
        by_name.setdefault(entry["coalition"], []).append(entry)
    for name, entries in by_name.items():
        found = []
        national = sorted(
            (e for e in entries if not _region(e["circles"])), key=lambda e: order.index(e["legislature"])
        )
        for e in national:
            last = found[-1] if found else None
            leg = e["legislature"]
            if last and (
                last["legislaturas"][-1] == leg or order.index(last["legislaturas"][-1]) + 1 == order.index(leg)
            ):
                page = last
            else:
                page = {"ambito": None, "legislaturas": [], "years": {}, "listas": set()}
                found.append(page)
            if leg not in page["legislaturas"]:
                page["legislaturas"].append(leg)
            page["years"][leg] = e["election_year"]
            page["listas"].add((leg, e["ballot_acronym"]))
        regional = {}
        for e in entries:
            region = _region(e["circles"])
            if region:
                page = regional.setdefault(
                    (e["legislature"], region),
                    {"ambito": region, "legislaturas": [e["legislature"]], "years": {}, "listas": set()},
                )
                page["years"][e["legislature"]] = e["election_year"]
                page["listas"].add((e["legislature"], e["ballot_acronym"]))
        found += regional.values()
        for page in found:
            page["legislaturas"].sort(key=order.index)
            page["eleicoes"] = [page["years"][leg] for leg in page["legislaturas"]]
            if len(found) == 1:
                page["id"] = name
                continue
            if page["eleicoes"][0] is None:
                raise ValueError(f"coalition {name!r} in {page['legislaturas'][0]} has no election year")
            parts = [_slug(name)]
            if page["ambito"] and _slug(page["ambito"]) not in _slug(name).split("-"):
                parts.append(_slug(page["ambito"]))
            page["id"] = "-".join([*parts, str(page["eleicoes"][0])])
        for page in found:
            del page["years"]
            page["sigla"] = name
        pages += found
    ids = [p["id"] for p in pages]
    if len(set(map(_slug, ids))) != len(ids):
        raise ValueError(f"two coalition pages share a path: {sorted(ids)}")
    return pages


def _coalition_lists(con):
    """[page] for every coalition list and run (coalition_pages), each with the seed rows of
    its lists, oldest short name first."""
    order = [leg["legislature"] for leg in reversed(repository.legislatures(con))]
    rows = repository.coalition_rows(con)
    years = repository.election_years(con)
    circles = {}
    lists = {}
    for r in rows:
        leg = r["legislature"]
        if leg not in circles:
            circles[leg] = repository.list_seat_circles(con, leg)
        key = (r["coalition"], leg, r["ballot_acronym"])
        if key not in lists:
            lists[key] = {
                "coalition": r["coalition"],
                "legislature": leg,
                "ballot_acronym": r["ballot_acronym"],
                "circles": circles[leg].get(r["ballot_acronym"]) if circles[leg] else None,
                "election_year": years.get(leg) or r["url_year"],
            }
    pages = coalition_pages(order, list(lists.values()))
    for c in pages:
        c["rows"] = [
            r for r in rows if r["coalition"] == c["sigla"] and (r["legislature"], r["ballot_acronym"]) in c["listas"]
        ]
    pages.sort(key=lambda c: (c["sigla"], order.index(c["legislaturas"][0]), c["ambito"] or ""))
    return pages


def _summary(con, c):
    """The page with its summary. It is active when it has the open legislature. Its
        components are the groups of all its legislatures (#214), largest in the latest one first,
        then those with seats in more of them, with com_lugares false for a group that won no seat
        on its lists in any of them, named as in the latest legislature that names them (the seed names
    a group only where it won seats); each legislature keeps its own groups and seat flags. Its dates
        are those of its legislatures."""
    latest = c["legislaturas"][-1]
    last = [r for r in c["rows"] if r["legislature"] == latest]
    by_leg = {}
    names = {}
    for r in c["rows"]:
        flags = by_leg.setdefault(r["legislature"], {})
        flags[r["group_code"]] = flags.get(r["group_code"], False) or bool(r["has_seats"])
        named = names.setdefault(r["group_code"], {})
        if r["group_name"]:
            named[r["legislature"]] = r["group_name"]
    seats = {g["group_acronym"]: g["seats"] for g in repository.seats_by_group(con, latest, last[0]["ref_day"])}
    with_seats = {g: sum(1 for flags in by_leg.values() if flags.get(g)) for g in names}

    def order(group):
        return (-seats.get(group, 0) if group in by_leg[latest] else 0, -with_seats[group], group)

    components = [
        {
            "sigla": g,
            "nome": names[g][max(names[g], key=c["legislaturas"].index)] if names[g] else g,
            "com_lugares": with_seats[g] > 0,
        }
        for g in sorted(names, key=order)
    ]
    partidos = {
        leg: [{"sigla": g, "com_lugares": by_leg[leg][g]} for g in sorted(by_leg[leg], key=order)]
        for leg in c["legislaturas"]
    }
    ativa = any(r["is_open"] for r in c["rows"])
    return {
        **c,
        "nome": sorted(r["coalition_name"] for r in last)[0],
        "legislature": latest,
        "ref_day": last[0]["ref_day"],
        "ativa": ativa,
        "data_formacao": _iso(min(r["start_date"] for r in c["rows"])),
        "data_dissolucao": None if ativa else _iso(max(r["end_date"] for r in c["rows"])),
        "components": components,
        "partidos_por_legislatura": partidos,
    }


def _coalition(con, coligacao_id):
    """The page with this id, or whose id has the same path form (coligacoes/cdu is CDU)."""
    for c in _coalition_lists(con):
        if c["id"] == coligacao_id or _slug(c["id"]) == _slug(coligacao_id):
            return _summary(con, c)
    raise NotFound(f"coligação {coligacao_id!r} não encontrada")


def coalition_link(con, legislature, group):
    """{id, sigla, nome} of the coalition page a group ran in for a legislature, the national
    list first, else None."""
    for c in sorted(_coalition_lists(con), key=lambda c: c["ambito"] is not None):
        rows = [r for r in c["rows"] if r["legislature"] == legislature and r["group_code"] == group]
        if rows:
            return {"id": c["id"], "sigla": c["sigla"], "nome": rows[0]["coalition_name"]}
    return None


def _coalition_seated(con, rows, legislature, day):
    """The deputies seated on ``day`` in one of the coalition's groups in a legislature, in a
    circle where the list they belong to won seats (#181). A list that ran only in Madeira or the
    Açores does not take the whole group. In a legislature without seats per circle every deputy
    of the groups counts."""
    rows = [r for r in rows if r["legislature"] == legislature]
    groups = sorted({r["group_code"] for r in rows})
    seated = repository.seated_in_groups(con, legislature, day, groups) if groups else []
    circles = repository.list_seat_circles(con, legislature)
    if not circles:
        return seated
    allowed = {(r["group_code"], circle) for r in rows for circle in circles.get(r["ballot_acronym"], ())}
    return [s for s in seated if (s["group_acronym"], s["circle"]) in allowed]


def _coalition_elected(con, rows, legislature, day):
    """(contagem, deputies): the deputies the coalition's lists elected in a legislature, as the
    election result has them (#197), with contagem "eleitos". Up to VI the release lists them
    (ballot_list_elected), with rows it could not match to a deputy. From VII on they come from
    the mandates: a deputy elected for one of the coalition's groups, in a circle where its list
    won seats. Both give each list exactly its seats (ballot_list_seats). A legislature with no
    seats per circle (Constituinte and I-A, where no coalition won seats) falls back to the
    deputies seated on ``day``, with contagem "em_funcoes"."""
    rows = [r for r in rows if r["legislature"] == legislature]
    ballots = sorted({r["ballot_acronym"] for r in rows})
    if repository.has_list_elected(con, legislature):
        return "eleitos", repository.list_elected(con, legislature, ballots)
    circles = repository.list_seat_circles(con, legislature)
    if not circles:
        return "em_funcoes", _coalition_seated(con, rows, legislature, day)
    allowed = {(r["group_code"], circle) for r in rows for circle in circles.get(r["ballot_acronym"], ())}
    elected = repository.elected_by_mandate(con, legislature)
    return "eleitos", [e for e in elected if (e["group_acronym"], e["circle"]) in allowed]


def _head(c):
    return {"id": c["id"], "sigla": c["sigla"], "nome": c["nome"], "tipo_coligacao": "eleitoral"}


def _coalition_dict(con, c, with_legislatures=False):
    contagem, elected = _coalition_elected(con, c["rows"], c["legislature"], c["ref_day"])
    seated = _coalition_seated(con, c["rows"], c["legislature"], c["ref_day"])
    out = {
        **_head(c),
        "ambito": c["ambito"],
        "eleicoes": c["eleicoes"],
        "ativa": c["ativa"],
        "data_formacao": c["data_formacao"],
        "data_dissolucao": c["data_dissolucao"],
        "legislatura": c["legislature"],
        "component_parties": [
            {"sigla": p["sigla"], "nome": p["nome"], "com_lugares": p["com_lugares"]} for p in c["components"]
        ],
        # The deputies elected on the lists (#197); who held the seat on the legislature's last
        # day (the data date for the open one) is the second figure.
        "deputy_count": len(elected),
        "contagem": contagem,
        "deputados_em_funcoes": len(seated),
        "data_em_funcoes": _iso(c["ref_day"]),
        "legislatura_aberta": c["ativa"],
        # Editorial fields with no source in the release: left empty, the page guards them.
        "espectro_politico": None,
        "observacoes": None,
    }
    if with_legislatures:
        out["legislaturas"] = []
        for leg, year in zip(c["legislaturas"], c["eleicoes"], strict=True):
            rows = [r for r in c["rows"] if r["legislature"] == leg]
            day = rows[0]["ref_day"]
            leg_contagem, leg_elected = _coalition_elected(con, c["rows"], leg, day)
            out["legislaturas"].append(
                {
                    "legislatura": leg,
                    "ano_eleicao": year,
                    "listas": sorted({r["ballot_acronym"] for r in rows}),
                    "deputados": len(leg_elected),
                    "em_funcoes": len(_coalition_seated(con, c["rows"], leg, day)),
                    "contagem": leg_contagem,
                    "partidos": c["partidos_por_legislatura"][leg],
                }
            )
    return out


def coligacoes(con, include_inactive=False):
    pages = [_summary(con, c) for c in _coalition_lists(con)]
    found = [_coalition_dict(con, c) for c in pages if include_inactive or c["ativa"]]
    return {"coligacoes": found, "total": len(found), "include_inactive": include_inactive}


def coligacao(con, coligacao_id):
    return _coalition_dict(con, _coalition(con, coligacao_id), with_legislatures=True)


def coligacao_deputados(con, coligacao_id, legislatura=None):
    c = _coalition(con, coligacao_id)
    leg = _legislature(con, legislatura) if legislatura else {"legislature": c["legislature"], "ref_day": c["ref_day"]}
    contagem, elected = _coalition_elected(con, c["rows"], leg["legislature"], leg["ref_day"])
    return {
        "coligacao": _head(c),
        "deputados": [
            {
                "id": e["cadastro_id"],
                "id_cadastro": e["cadastro_id"],
                "nome": e["parliamentary_name"],
                "nome_completo": e["full_name"],
                "partido_sigla": e["group_acronym"],
                "circulo": e["circle"],
                "picture_url": PICTURE_URL.format(e["cadastro_id"]) if e["cadastro_id"] is not None else None,
            }
            for e in elected
        ],
        "total_deputados": len(elected),
        "contagem": contagem,
        "legislatura": leg["legislature"],
    }


def coligacao_partidos(con, coligacao_id):
    c = _coalition(con, coligacao_id)
    first = {}
    for r in c["rows"]:
        first.setdefault(r["group_code"], r["start_date"])
    parties = [
        {
            "sigla": p["sigla"],
            "nome": p["nome"],
            "com_lugares": p["com_lugares"],
            "data_adesao": _iso(first.get(p["sigla"])),
            "papel_coligacao": None,
        }
        for p in c["components"]
    ]
    return {
        "coligacao": _head(c),
        "partidos": parties,
        "total_partidos": len(parties),
    }


def _published(con):
    release = repository.release(con)
    return bool(release and release["published"])


def health(con):
    """The live release: tag, schema version, source_updated, data commit and sync time, as
    text, and whether the tag is a published GitHub release (publicado) or a local build of the
    pin. The footer shows the tag and source_updated on every page, and links the tag only
    when it is published."""
    meta = repository.meta(con) or {}
    data = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in meta.items()}
    if meta:
        data["publicado"] = _published(con)
    return {"status": "healthy", "service": SERVICE, "data": data}


CC_BY = "CC BY 4.0"


def dados(con):
    """The download page (/dados, #186): the live release's manifest.json with the real size of
    each file. publicado says whether the release is on GitHub; only then do the files have a
    download URL (a local build of the pin has a tag that GitHub doesn't know)."""
    meta = repository.meta(con) or {}
    release = repository.release(con)
    manifest = json.loads(release["manifest"]) if release else {}
    published = bool(release and release["published"])
    files = {f["name"]: f for f in repository.release_files(con)}
    default_licence = (
        (manifest.get("licence") or {}).get("marts") if isinstance(manifest.get("licence"), dict) else None
    )

    def file(name):
        if not name or name not in files:
            return None
        f = files[name]
        return {"nome": name, "bytes": f["bytes"], "url": f["url"] if published else None}

    sets = []
    for name, entry in (manifest.get("marts") or {}).items():
        names = {kind: (spec or {}).get("name") for kind, spec in (entry.get("files") or {}).items()}
        licence = entry.get("licence") or default_licence or CC_BY
        sets.append(
            {
                "nome": name,
                "linhas": entry.get("rows"),
                "licenca": licence,
                "cc_by": licence == CC_BY,
                "parquet": file(names.get("parquet")),
                "csv": file(names.get("csv")),
            }
        )

    def total(kind):
        return sum((s[kind] or {}).get("bytes") or 0 for s in sets)

    return {
        "tag": meta.get("tag") or manifest.get("tag"),
        "source_updated": manifest.get("source_updated") or meta.get("source_updated"),
        "data_commit": manifest.get("data_commit"),
        "schema_version": manifest.get("schema_version"),
        "publicado": published,
        "release_url": release["url"] if published else None,
        "manifest": file("manifest.json"),
        "changelog": file("CHANGELOG.md"),
        "conjuntos": sets,
        "total_parquet": total("parquet"),
        "total_csv": total("csv"),
    }
