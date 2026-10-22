"""Party page: the group's deputies and their demographics (F22, F23).

The list is everyone who held a seat for the group in any legislature (or in ``legislatura``),
one row each. The demographics cover the group's deputies seated on the legislature's
reference day, so the figures of every group in a legislature add up to its seats. Education
(F24) waits for qualifications in the release, and there is no source for an urban/rural
split, so neither is in the payload.
"""

from statistics import median

from app.data import repository
from app.services.core import PICTURE_URL, NotFound, _legislature

SEX = {"M": "Masculino", "F": "Feminino"}
COHORTS = [(35, "< 35 anos"), (45, "35-44 anos"), (55, "45-54 anos"), (65, "55-64 anos"), (None, "65+ anos")]
REGIONS = {
    "Norte": ["Braga", "Bragança", "Porto", "Viana do Castelo", "Vila Real"],
    "Centro": ["Aveiro", "Castelo Branco", "Coimbra", "Guarda", "Leiria", "Viseu"],
    "Lisboa e Vale do Tejo": ["Lisboa", "Santarém", "Setúbal"],
    "Alentejo": ["Beja", "Évora", "Portalegre"],
    "Algarve": ["Faro"],
    "Açores": ["Açores"],
    "Madeira": ["Madeira"],
    "Emigração": ["Europa", "Fora da Europa"],
}
REGION_OF = {circle: region for region, circles in REGIONS.items() for circle in circles}
# First match wins, on the lower-cased profession as the register publishes it.
PROFESSIONS = [
    ("Direito", ["advogad", "jurista", "direito", "magistrad", "solicitador"]),
    ("Educação", ["professor", "docente", "educa"]),
    ("Saúde", ["médic", "enfermeir", "saúde", "farmacêutic"]),
    ("Engenharia/Técnico", ["engenheir", "engenharia", "técnic"]),
    ("Economia/Gestão", ["economista", "gestor", "gestora", "gestão", "empresári", "contabilista"]),
    ("Política", ["polític", "deputad", "autarca", "vereador", "presidente"]),
]


def region(circle):
    return REGION_OF.get(circle, "Outros")


def profession_category(profession):
    text = profession.strip().lower()
    return next((name for name, words in PROFESSIONS if any(w in text for w in words)), "Outras")


def _age(birth, day):
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


def _cohort(age):
    return next(label for limit, label in COHORTS if limit is None or age < limit)


def _count(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def _experience(served):
    if served == 1:
        return "Primeiro Mandato"
    return "Experiente (2-3 mandatos)" if served <= 3 else "Muito Experiente (4+ mandatos)"


def _demographics(seated, day, people):
    aged = [(p, _age(p["birth_date"], day)) for p in seated if p["birth_date"] is not None]
    ages = [a for _, a in aged]
    professions = [profession_category(p["profession"]) for p in seated if p["profession"]]
    new = sum(1 for p in seated if p["legislatures_served"] == 1)

    def person(row, age):
        return {**people[row["cadastro_id"]], "idade": age}

    return {
        "genero": _count(SEX.get(p["sex"], p["sex"]) for p in seated if p["sex"]),
        "profissoes": {"categorias": _count(professions), "total_especificadas": len(professions)},
        "idades": {
            "cohorts_geracionais": _count(_cohort(a) for a in ages),
            "idade_media": round(sum(ages) / len(ages), 1) if ages else None,
            "idade_mediana": round(median(ages), 1) if ages else None,
            "min": min(ages) if ages else None,
            "max": max(ages) if ages else None,
            "total_com_idade": len(ages),
            "sem_idade": len(seated) - len(ages),
            # Oldest by birth date, ties to the lower id; youngest the other way round.
            "oldest_deputy": person(*min(aged, key=lambda x: (x[0]["birth_date"], x[0]["cadastro_id"])))
            if aged
            else None,
            "youngest_deputy": person(*max(aged, key=lambda x: (x[0]["birth_date"], -x[0]["cadastro_id"])))
            if aged
            else None,
        },
        "geografia": {
            "regional": _count(region(p["circle"]) for p in seated),
            "circulos": _count(p["circle"] for p in seated),
        },
        "renovacao": {
            "novos_deputados": new,
            "veteranos": len(seated) - new,
            "percentual_renovacao": round(new / len(seated) * 100, 1) if seated else 0,
        },
        "experiencia_politica": {
            "categorias": _count(_experience(p["legislatures_served"]) for p in seated),
            "mandatos_anteriores": _count(str(p["legislatures_served"]) for p in seated),
        },
    }


def _periodo(rows):
    first = min(r["legislature_start"] for r in rows).year
    if any(r["legislature_end"] is None for r in rows):
        return f"desde {first}"
    return f"{first}-{max(r['legislature_end'] for r in rows).year}"


def partido_deputados(con, sigla, legislatura=None):
    name = repository.group_name(con, sigla)
    if name is None:
        raise NotFound(f"partido {sigla!r} não encontrado")
    current = _legislature(con)
    leg = _legislature(con, legislatura) if legislatura else current
    rows = repository.group_service(con, sigla, legislatura)
    active = {s["cadastro_id"] for s in repository.group_seated(con, current["legislature"], current["ref_day"], sigla)}
    latest = {}
    for r in rows:
        latest[r["cadastro_id"]] = r
    people = {
        cad: {
            "id": cad,
            "id_cadastro": cad,
            "nome": r["parliamentary_name"],
            "nome_completo": r["full_name"] or r["parliamentary_name"],
            "profissao": r["profession"],
            "picture_url": PICTURE_URL.format(cad),
            "circulo": r["circle"],
            "ultima_legislatura": r["legislature"],
            "mandato_ativo": cad in active,
        }
        for cad, r in latest.items()
    }
    deputies = sorted(people.values(), key=lambda d: (not d["mandato_ativo"], d["nome"], d["id"]))
    seated = repository.group_seated(con, leg["legislature"], leg["ref_day"], sigla)
    coalition = next(
        (
            {"sigla": c["coalition"], "nome": c["coalition_name"]}
            for c in repository.coalition_rows(con)
            if c["legislature"] == leg["legislature"] and c["group_code"] == sigla
        ),
        None,
    )
    return {
        "partido": {"sigla": sigla, "nome": name},
        "coligacao": coalition,
        "legislatura": leg["legislature"],
        "deputados": deputies,
        "total": len(deputies),
        "mandatos_ativos": sum(1 for d in deputies if d["mandato_ativo"]),
        "historico": {
            "total_legislaturas": len({r["legislature"] for r in rows}),
            "total_circulos": len({r["circle"] for r in rows if r["circle"]}),
            "periodo_atividade": _periodo(rows) if rows else None,
        },
        "demografia": _demographics(seated, leg["ref_day"], people),
    }
