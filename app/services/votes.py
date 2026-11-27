"""One page per plenary vote (#191).

``votacao`` is the payload of /votacoes/:id: the result, the phase and the initiatives the vote
decided, the group positions exactly as the AR published them (rows inferred from a unanimous
vote are left out, so a unanimous vote shows "Unanimidade" and no groups), and the deputies
the AR named, apart from the group counts. Nothing is computed from group sizes: no margins.

The static export holds every plenary vote in one file per VOTE_GROUP ids
(``votacoes/grupo/<id // VOTE_GROUP>.json``) and lists the votes of STATIC_PAGE_LEGISLATURES
in ``votacoes/paginas.json``, which deploy/pages.py turns into one HTML page each, with its own
title and description. Other votes have no page file: the app loads them from their group.
"""

from collections import defaultdict

from app.data import repository
from app.services.core import NotFound, _iso
from app.services.voting import INITIATIVE_URL

__all__ = ["NotFound", "paginas", "votacao", "votacoes_por_grupo"]

VOTE_GROUP = 1000
STATIC_PAGE_LEGISLATURES = ("XVII",)
POSITIONS = {"favour": "favor", "against": "contra", "abstention": "abstencao", "absent": "ausentes"}
NAMED = {"favour": "favor", "against": "contra", "abstention": "abstencao", "absent": "ausente"}
TITLE_MAX = 110


def vote_group(vote_id):
    """The id range a vote's file holds: the thousand it is in."""
    return vote_id // VOTE_GROUP


def _initiative(row):
    return {
        "id": row["initiative_id"],
        "legislatura": row["legislature"],
        "tipo": row["type"],
        "numero": row["number"],
        "titulo": row["title"].strip() if row["title"] else row["title"],
        "fase": row["phase"],
        "autoria": list(row["authors"] or []),
        "url": INITIATIVE_URL.format(row["initiative_id"]),
    }


def _payloads(con, lo=None, hi=None):
    """{vote_id: payload} for the plenary votes with lo <= vote_id < hi."""
    positions = defaultdict(lambda: {key: [] for key in POSITIONS.values()})
    for p in repository.plenary_published_positions(con, lo, hi):
        positions[p["vote_id"]][POSITIONS[p["position"]]].append({"grupo": p["group_code"], "deputados": p["deputies"]})
    named = defaultdict(list)
    for d in repository.plenary_named_votes(con, lo, hi):
        named[d["vote_id"]].append(
            {
                "nome": d["name"],
                "grupo": d["group_code"],
                "posicao": NAMED[d["position"]],
                "id_cadastro": d["cadastro_id"],
            }
        )
    out = {}
    for v in repository.plenary_vote_rows(con, lo, hi):
        initiatives = [_initiative(i) for i in v["initiatives"] or []]
        # A missing phase counts too: one initiative with none means there is no shared phase.
        phases = {i["fase"] for i in initiatives}
        out[v["vote_id"]] = {
            "id": v["vote_id"],
            "legislatura": v["legislature"],
            "data": _iso(v["date"]),
            "resultado": v["result"],
            "unanimidade": bool(v["unanimous"]),
            "descricao": v["description"],
            # The phase of the vote when its initiatives share one.
            "fase": phases.pop() if len(phases) == 1 else None,
            "iniciativas": initiatives,
            "posicoes": positions[v["vote_id"]],
            "votos_nomeados": named[v["vote_id"]],
        }
    return out


def votacao(con, vote_id):
    """The page of one plenary vote. NotFound for any other id, committee votes included."""
    found = _payloads(con, vote_id, vote_id + 1).get(vote_id)
    if found is None:
        raise NotFound(f"Votação {vote_id} não encontrada")
    return found


def votacoes_por_grupo(con):
    """{group: {"votacoes": {"<id>": payload}}} for every plenary vote, as the export writes it."""
    groups = defaultdict(dict)
    for vote_id, payload in _payloads(con).items():
        groups[vote_group(vote_id)][str(vote_id)] = payload
    return {g: {"votacoes": votes} for g, votes in sorted(groups.items())}


def short_title(text):
    """A page title of at most TITLE_MAX characters, cut at a word."""
    text = " ".join(str(text).split())
    if len(text) <= TITLE_MAX:
        return text
    cut = text[: TITLE_MAX - 1].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def _day(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def _initiative_name(i):
    name = i["tipo"] or "Iniciativa"
    if i["numero"] is not None:
        name += f" n.º {i['numero']}/{i['legislatura']}"
    return f"{name}: {i['titulo']}" if i["titulo"] else name


def page_head(v):
    """(title, description) of a vote's page, for the HTML head and link previews (#183)."""
    if v["iniciativas"]:
        title = _initiative_name(v["iniciativas"][0])
        if len(v["iniciativas"]) > 1:
            title += f" (e mais {len(v['iniciativas']) - 1})"
    else:
        title = v["descricao"] or f"Votação {v['id']} no Plenário de {_day(v['data'])}"
    result = v["resultado"] or "Resultado não publicado"
    if v["unanimidade"]:
        result += " por unanimidade"
    parts = [f"Votação no Plenário a {_day(v['data'])}: {result}."]
    if v["fase"]:
        parts.append(f"{v['fase']}.")
    parts.append("Posições dos grupos parlamentares tal como a Assembleia da República as publica.")
    return short_title(title), " ".join(parts)


def paginas(con):
    """The votes that get a page file of their own (STATIC_PAGE_LEGISLATURES), with its head."""
    entries = []
    for v in _payloads(con).values():
        if v["legislatura"] in STATIC_PAGE_LEGISLATURES:
            title, description = page_head(v)
            entries.append({"id": v["id"], "titulo": title, "descricao": description})
    return {"legislaturas": list(STATIC_PAGE_LEGISLATURES), "votacoes": entries}
