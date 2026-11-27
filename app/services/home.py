"""The home page (#265): the composition strip with the mandate changes of the last 30 days,
and the state of the sources.

Seats and changes come from the mandates and group memberships on the legislature's
reference day (the extract date of the data), never from today's date. Gaps in the data are
reported as coverage of the sources, not as a political problem.
"""

from datetime import timedelta

from app.data import repository
from app.services.core import _legislature

# The groups of the parties that form the Government, by legislature, with the Government's
# own page as the source. The AR data does not say which parties form the Government. Change it
# with a new Government, in its own commit.
GOVERNMENTS = {
    "XVII": {
        "nome": "XXV Governo Constitucional",
        "grupos": ("PSD", "CDS-PP"),
        "fonte": "https://www.portugal.gov.pt/pt/gc25",
    },
}
CHANGE_DAYS = 30


def _iso(day):
    return day.isoformat() if day is not None else None


def _pt(day):
    return day.strftime("%d/%m/%Y")


def _composicao(con):
    leg = _legislature(con)
    name, day = leg["legislature"], leg["ref_day"]
    government = GOVERNMENTS.get(name)
    supports = set(government["grupos"]) if government else set()
    groups = repository.seats_by_group(con, name, day)
    groups.sort(key=lambda g: g["group_acronym"] not in supports)  # stable: by seats within each part
    since = day - timedelta(days=CHANGE_DAYS - 1)
    return {
        "data": _iso(day),
        "legislatura": name,
        "lugares": sum(g["seats"] for g in groups),
        "substituicoes_temporarias": repository.temporary_seats(con, name, day),
        "governo": {"nome": government["nome"], "fonte": government["fonte"]} if government else None,
        "grupos": [
            {
                "sigla": g["group_acronym"],
                "nome": g["name"] or g["group_acronym"],
                "deputados": g["seats"],
                "apoia_governo": g["group_acronym"] in supports,
            }
            for g in groups
        ],
        "mudancas": {
            "desde": _iso(since),
            "ate": _iso(day),
            "itens": [
                {
                    "data": _iso(c["day"]),
                    "cadastro_id": c["cadastro_id"],
                    "nome": c["name"],
                    "grupo": c["group_acronym"],
                    "evento": c["event"],
                    "situacao": c["situation"],
                }
                for c in repository.mandate_changes(con, name, since, day)
            ],
        },
    }


def _missing_declarations(con):
    """The legislatures after the last one with interest declarations, as 'XVI e da XVII'."""
    with_declarations = set(repository.interest_declaration_legislatures(con))
    names = [leg["legislature"] for leg in reversed(repository.legislatures(con))]  # oldest first
    if not with_declarations:
        return None
    last = max(i for i, n in enumerate(names) if n in with_declarations)
    missing = names[last + 1 :]
    if not missing:
        return None
    return missing[0] if len(missing) == 1 else ", da ".join(missing[:-1]) + " e da " + missing[-1]


def _fontes(con, mandates_day):
    meta = repository.meta(con) or {}
    dates = repository.dataset_dates(con) or {}
    gaps = []
    votes, interventions = dates.get("votes"), dates.get("interventions")
    if votes and interventions and interventions < votes:
        gaps.append(
            {
                "tipo": "atraso",
                "conjunto": "Intervenções",
                "texto": f"A AR publicou intervenções até {_pt(interventions)}, e as votações vão até {_pt(votes)}.",
            }
        )
    missing = _missing_declarations(con)
    if missing:
        gaps.append(
            {
                "tipo": "em_falta",
                "conjunto": "Declarações de interesses",
                "texto": f"As declarações da {missing} estão na Entidade para a Transparência e aguardam autorização de reutilização.",
            }
        )
    return {
        "tag": meta.get("tag"),
        "source_updated": meta.get("source_updated"),
        "conjuntos": [
            {"nome": "Votações em Plenário", "dados_ate": _iso(votes)},
            {"nome": "Iniciativas", "dados_ate": _iso(dates.get("initiatives"))},
            {"nome": "Intervenções", "dados_ate": _iso(interventions)},
            {"nome": "Mandatos", "dados_ate": mandates_day},
        ],
        "lacunas": gaps,
    }


def inicio(con):
    """{composicao, fontes} for the home page."""
    composicao = _composicao(con)
    return {"composicao": composicao, "fontes": _fontes(con, composicao["data"])}
