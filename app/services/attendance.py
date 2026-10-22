"""Plenary attendance (F12) from the plenary_attendance mart of the parlamento-aberto release.

The lists hold whoever had a seat at each sitting, substitutes included, from the VI
Legislature on (one sitting in the V). The rate is present, in another body or on mission
(official parliamentary work), over the ordinary and extraordinary sittings in the lists.
Solemn and commemorative sittings are counted apart and stay out of the rate. The strict
rate, present only, goes next to it, and every category is shown, so any other reading can
be worked out. No default, no cap, and the session count always goes with a rate.

Only the code is published, never the reason for an absence. Code meanings are the ones
parlamento-aberto cites in its attendance_codes seed (the AR's own sitting pages and
Resolução da AR n.º 21/2009); the release ships the category of each row, not the seed.
"""

from app.data import repository
from app.services.core import _iso
from app.services.deputies import _person

__all__ = ["CODES", "DEFINITION", "deputado_attendance", "latest_rate", "year_average"]

# code: (meaning, category), as in parlamento-aberto's seeds/attendance_codes.csv.
CODES = {
    "PR": ("Presença", "present"),
    "PT": ("Presença (código usado até fevereiro de 2021)", "present"),
    "PP": ("Presença (código usado até março de 2009)", "present"),
    "PNO": ("Presença noutro órgão", "other_body_or_mission"),
    "CO": ("Presença em comissão autorizada pelo Presidente da AR", "other_body_or_mission"),
    "ME": ("Ausência em missão parlamentar", "other_body_or_mission"),
    "MP": ("Ausência em missão parlamentar", "other_body_or_mission"),
    "FJ": ("Falta justificada", "justified"),
    "FIJ": ("Falta justificada", "justified"),
    "FAJ": ("Falta justificada", "justified"),
    "QVJ": ("Falta ao quórum de votação, justificada", "justified"),
    "QV": ("Falta ao quórum de votação", "missed_quorum_vote"),
    "FA": ("Falta ainda sem classificação", "pending"),
    "FI": ("Falta injustificada", "unjustified"),
}
# Mart category: key in the payload.
CATEGORIES = {
    "present": "presente",
    "other_body_or_mission": "outro_orgao_ou_missao",
    "justified": "justificadas",
    "missed_quorum_vote": "quorum_votacao",
    "pending": "por_justificar",
    "unclassified": "nao_classificadas",
    "unjustified": "injustificadas",
}
DEFINITION = {
    "taxa_presenca": (
        "Presenças, presenças noutro órgão ou em comissão autorizada e ausências em missão parlamentar, "
        "sobre as reuniões plenárias ordinárias e extraordinárias nas listas de presenças."
    ),
    "taxa_presenca_estrita": "Só as presenças no Plenário, sobre as mesmas reuniões.",
    "solenes": "As reuniões solenes e comemorativas contam à parte e ficam fora das taxas.",
    "por_justificar": (
        "Uma falta FA com menos de 60 dias na data dos dados ainda pode ser justificada; "
        "a partir daí fica não classificada. Nunca conta como injustificada."
    ),
    "cobertura": "A AR publica listas de presenças a partir da VI Legislatura (uma reunião na V).",
    "motivo": "O motivo de cada falta não é publicado, só o código.",
}


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else None


def _counts(row):
    return {key: (row[cat] if row else 0) for cat, key in CATEGORIES.items()}


def _rates(row):
    meetings = row["meetings"] if row else 0
    attended = (row["present"] + row["other_body_or_mission"]) if row else 0
    return meetings, _pct(attended, meetings), _pct(row["present"] if row else 0, meetings)


def _record(row):
    meaning, _ = CODES.get(row["code"], (row["code"], None))
    return {
        "data": _iso(row["meeting_date"]),
        "reuniao_id": row["meeting_id"],
        "tipo_reuniao": row["meeting_type"],
        "solene": bool(row["is_ceremonial"]),
        "codigo": row["code"],
        "categoria": row["category"],
        "descricao": meaning,
        "grupo": row["group_code"],
    }


def _legislature(name, is_open, rows, pooled, records):
    if pooled is None:
        return {
            "legislatura": name,
            "em_curso": is_open,
            "com_listas": False,
            "grupos": [],
            "reunioes": None,
            "contagens": None,
            "taxa_presenca": None,
            "taxa_presenca_estrita": None,
            "solenes": None,
            "primeira_reuniao": None,
            "ultima_reuniao": None,
            "legislatura_taxa_presenca": None,
            "legislatura_taxa_presenca_estrita": None,
            "registos": [],
        }
    ordinary = rows.get(False)
    solemn = rows.get(True)
    meetings, rate, strict = _rates(ordinary)
    both = [r for r in (ordinary, solemn) if r]
    return {
        "legislatura": name,
        "em_curso": is_open,
        "com_listas": True,
        "grupos": sorted({g for r in both for g in r["groups"]}),
        "reunioes": meetings,
        "contagens": _counts(ordinary),
        "taxa_presenca": rate,
        "taxa_presenca_estrita": strict,
        "solenes": {"reunioes": solemn["meetings"] if solemn else 0, "contagens": _counts(solemn)},
        "primeira_reuniao": _iso(min(r["first_meeting"] for r in both)) if both else None,
        "ultima_reuniao": _iso(max(r["last_meeting"] for r in both)) if both else None,
        "legislatura_taxa_presenca": _pct(pooled["attended"], pooled["seats"]),
        "legislatura_taxa_presenca_estrita": _pct(pooled["present"], pooled["seats"]),
        "registos": [_record(r) for r in records],
    }


def deputado_attendance(con, cadastro_id):
    """Attendance in every legislature the person held a seat in, newest first."""
    _, career = _person(con, cadastro_id)
    names = [c["legislature"] for c in career]
    by_leg = {}
    for row in repository.attendance_by_legislature(con, [cadastro_id]):
        by_leg.setdefault(row["legislature"], {})[bool(row["is_ceremonial"])] = row
    pooled = {r["legislature"]: r for r in repository.attendance_legislatures(con, names)}
    records = {}
    for row in repository.attendance_records(con, cadastro_id):
        records.setdefault(row["legislature"], []).append(row)
    meta = repository.meta(con)
    return {
        "id_cadastro": cadastro_id,
        "legislaturas": [
            _legislature(
                c["legislature"],
                bool(c["is_open"]),
                by_leg.get(c["legislature"], {}),
                pooled.get(c["legislature"]),
                records.get(c["legislature"], []),
            )
            for c in reversed(career)
        ],
        "codigos": [{"codigo": code, "descricao": m, "categoria": cat} for code, (m, cat) in CODES.items()],
        "definicao": DEFINITION,
        "atualizado": meta["source_updated"],
    }


def latest_rate(attendance, career):
    """The profile card: the latest legislature the person served in that has lists.
    ``attendance``: the person's attendance_by_legislature rows."""
    rows = {}
    for row in attendance:
        if not row["is_ceremonial"]:
            rows[row["legislature"]] = row
    for c in reversed(career):
        row = rows.get(c["legislature"])
        if row and row["meetings"]:
            meetings, rate, strict = _rates(row)
            return {
                "legislatura": c["legislature"],
                "reunioes": meetings,
                "taxa_presenca": rate,
                "taxa_presenca_estrita": strict,
            }
    return None


def year_average(con, legislature, start, end):
    """Seats attended over seats on the lists of the sittings between two days, or None."""
    row = repository.attendance_between(con, legislature, start, end)
    if not row or not row["seats"]:
        return None
    return {"media_presencas": _pct(row["attended"], row["seats"]), "reunioes": row["meetings"]}
