"""Plenary decisions (#263): the votes of the last plenary day that the published rule counts as
decisions. The rule and its SQL live in app/data/repository.py (plenary_decisions); this module
shapes them for the pages that show them, such as the home page's Decisões do Plenário (#264)."""

from app.data import repository


def _initiative(row):
    return {
        "id": row["initiative_id"],
        "legislatura": row["legislature"],
        "tipo": row["type"],
        "numero": row["number"],
        "titulo": (row["title"] or "").strip() or None,
        "autoria": row["author_kind"],
    }


def decisions_of(con, day):
    """The decisions of one plenary day, by vote id."""
    return [
        {
            "vote_id": row["vote_id"],
            "data": row["date"].isoformat(),
            "fase": row["phase"],
            "tipo": "final" if row["is_final"] else "generalidade",
            "resultado": row["result"],
            "unanimidade": bool(row["unanimous"]),
            "iniciativas": [_initiative(i) for i in row["initiatives"]],
        }
        for row in repository.plenary_decisions(con, day)
    ]


def latest_decisions(con):
    """{data, decisoes}: the last day with plenary votes in the data, and its decisions."""
    day = repository.last_plenary_vote_day(con)
    if day is None:
        return {"data": None, "decisoes": []}
    return {"data": day.isoformat(), "decisoes": decisions_of(con, day)}


POSITIONS = {"favour": "favor", "against": "contra", "abstention": "abstencao", "absent": "ausentes"}
GOVERNMENT = "Governo"


def _government(decisoes):
    """The decisions on an initiative the Government authored, and the rejected ones. Only the
    authorship the AR publishes counts: no reading of who supports the Government."""
    own = [d for d in decisoes if any(i["autoria"] == GOVERNMENT for i in d["iniciativas"])]
    rejected = [d["vote_id"] for d in own if (d["resultado"] or "").lower().startswith("rejeitad")]
    return {"votadas": len(own), "rejeitadas": rejected}


def decisoes_plenario(con):
    """The home page's Decisões do Plenário (#264): the decisions of the last plenary day, each
    with the group positions the AR published, and the Government's initiatives among them."""
    latest = latest_decisions(con)
    decisoes = latest["decisoes"]
    positions = {d["vote_id"]: {key: [] for key in POSITIONS.values()} for d in decisoes}
    for p in repository.published_group_positions(con, list(positions)):
        positions[p["vote_id"]][POSITIONS[p["position"]]].append({"grupo": p["group_code"], "deputados": p["deputies"]})
    decisoes = [{**d, "posicoes": positions[d["vote_id"]]} for d in decisoes]
    return {"data": latest["data"], "decisoes": decisoes, "governo": _government(decisoes)}
