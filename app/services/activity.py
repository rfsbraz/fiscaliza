"""Agenda page: recent plenary votes and activity stats (F33, F34).

Groups' positions are shown as the release publishes them, by group with a count where a
group split; the release has no per-deputy tallies. Figures with no source yet (attendance,
F12; committee meetings and hearings, F32) are left out, not sent as zeros.
"""

from datetime import date

from app.data import repository
from app.services.core import NotFound, _iso, _legislature

__all__ = ["NotFound", "estatisticas_atividade", "votacoes_recentes"]

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
POSITIONS = {"favour": "favor", "against": "contra", "abstention": "abstencao", "absent": "ausentes"}


def _title(vote):
    titles = vote["titles"] or []
    if not titles:
        return vote["description"] or f"Votação {vote['vote_id']}"
    return titles[0] if len(titles) == 1 else f"{titles[0]} (e mais {len(titles) - 1})"


def _description(vote):
    parts = [p for p in (vote["phase"], vote["description"] if vote["titles"] else None) if p]
    return ". ".join(parts) or None


def votacoes_recentes(con, limite=DEFAULT_LIMIT, legislatura=None):
    leg = _legislature(con, legislatura)
    limit = min(max(limite, 1), MAX_LIMIT)
    votes = repository.recent_plenary_votes(con, leg["legislature"], limit)
    groups = {v["vote_id"]: {key: [] for key in POSITIONS.values()} for v in votes}
    for p in repository.group_positions(con, list(groups)):
        label = p["group_code"] if p["deputies"] is None else f"{p['group_code']} ({p['deputies']})"
        groups[p["vote_id"]][POSITIONS[p["position"]]].append(label)
    out = [
        {
            "id": v["vote_id"],
            "data": _iso(v["date"]),
            "titulo": _title(v),
            "descricao": _description(v),
            "resultado": v["result"],
            "unanime": bool(v["unanimous"]),
            **groups[v["vote_id"]],
        }
        for v in votes
    ]
    results = [(v["resultado"] or "").lower() for v in out]
    return {
        "votacoes": out,
        "total": len(out),
        "legislatura": leg["legislature"],
        "resumo": {
            "aprovadas": sum(r.startswith("aprovad") for r in results),
            "rejeitadas": sum(r.startswith("rejeitad") for r in results),
            "periodo": f"Legislatura {leg['legislature']}, últimas {len(out)} votações em plenário",
        },
    }


def estatisticas_atividade(con):
    """Counts for the calendar year of the current legislature's reference day, up to that day."""
    day = _legislature(con)["ref_day"]
    counts = repository.activity_counts(con, date(day.year, 1, 1), day)
    decided = counts["approved"] + counts["rejected"]
    meta = repository.meta(con)
    return {
        "periodo": str(day.year),
        "data_referencia": _iso(day),
        "ultima_atualizacao": meta["source_updated"],
        "estatisticas": {
            "sessoes_plenarias": {"total_ano": counts["plenary_days"]},
            "votacoes": {
                "total_ano": counts["votes"],
                "aprovadas": counts["approved"],
                "rejeitadas": counts["rejected"],
                "taxa_aprovacao": round(counts["approved"] / decided * 100, 1) if decided else None,
            },
            "iniciativas": {"apresentadas": counts["initiatives"]},
            "intervencoes": {"total": counts["interventions"]},
        },
    }
