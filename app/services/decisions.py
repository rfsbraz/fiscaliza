"""Plenary decisions (#263): the votes of the last plenary day that the published rule counts as
decisions. The rule and its SQL live in app/data/repository.py (plenary_decisions); this module
shapes them for the pages that show them."""

from app.data import repository


def _initiative(row):
    return {
        "id": row["initiative_id"],
        "legislatura": row["legislature"],
        "tipo": row["type"],
        "numero": row["number"],
        "titulo": row["title"],
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
