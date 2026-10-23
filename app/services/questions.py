"""Written questions to the Government (#114): per legislature, the answer rate and the median
days to answer, per recipient.

A pergunta is a written question to the central administration. A question to two recipients
counts once for each recipient and once in the legislature totals, as answered when at least one
recipient answered. Withdrawn and returned ones are owed no answer: they are counted apart and
left out of the rate and the median. An answer with no usable date (missing, or before the date
sent) counts as answered and stays out of the median (``respondidas_sem_data``). The open
legislature is provisional, as recent perguntas may still get an answer. No deadline figure: the
legal answer period is not checked yet.
"""

from app.data import repository
from app.services.core import NotFound, _iso


def _rate(answered, total):
    return round(100 * answered / total, 1) if total else None


def _figures(row):
    return {
        "perguntas": row["perguntas"],
        "respondidas": row["respondidas"],
        "taxa_resposta": _rate(row["respondidas"], row["perguntas"]),
        "mediana_dias": row["mediana_dias"],
        "respondidas_sem_data": row["respondidas_sem_data"],
        "retiradas": row["retiradas"],
        "devolvidas": row["devolvidas"],
    }


def perguntas(con):
    """Every legislature with perguntas to the Government, newest first."""
    return {
        "legislaturas": [
            {
                "legislatura": row["legislature"],
                "provisoria": row["is_open"],
                "perguntas": row["perguntas"],
                "respondidas": row["respondidas"],
                "taxa_resposta": _rate(row["respondidas"], row["perguntas"]),
                "mediana_dias": row["mediana_dias"],
            }
            for row in repository.question_totals(con)
        ]
    }


def perguntas_legislatura(con, legislatura):
    """One legislature: its totals and the figures per recipient."""
    found = repository.question_totals(con, legislatura)
    if not found:
        raise NotFound(f"não há perguntas ao Governo na legislatura {legislatura!r}")
    row = found[0]
    return {
        "legislatura": row["legislature"],
        "provisoria": row["is_open"],
        "data_inicio": _iso(row["start_date"]),
        "data_fim": _iso(row["end_date"]),
        "totais": _figures(row),
        "destinatarios": [
            {"destinatario": r["recipient"], **_figures(r)} for r in repository.question_recipients(con, legislatura)
        ],
    }
