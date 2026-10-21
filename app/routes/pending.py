"""Endpoints the frontend calls whose data is not on the DuckDB layer yet.

Each answers 503 with a short reason and the step that brings it back. The frontend reads any
non-2xx answer as "not available" and shows its notice, so the page keeps working. None of
these touch the data file.

Permanent until their mart is released:
- attendance (F12) waits on the plenary attendance mart, S11;
- the agenda for today and this week (F32) waits on the agenda mart, S13.

Temporary, only until S5 (#68), S6 (#79) and S7 (#81) merge and register the real routes:
deputy details, activities, interests, voting analytics and the party deputies and voting
pages. tests/test_pending_endpoints.py fails on a route registered twice, so each stub goes in
the master merge that brings its real route.
"""

from flask import Blueprint, jsonify

pending_bp = Blueprint("pending", __name__)


def _pending(reason, planned):
    return jsonify({"status": "not_available", "reason": reason, "planned": planned}), 503


@pending_bp.route("/deputados/<int:cad_id>/attendance", methods=["GET"])
def get_deputado_attendance(cad_id):
    return _pending("Plenary attendance is not in the parlamento-aberto release yet.", "S11")


@pending_bp.route("/agenda/hoje", methods=["GET"])
def get_agenda_hoje():
    return _pending("The parliamentary agenda is not in the parlamento-aberto release yet.", "S13")


@pending_bp.route("/agenda/semana", methods=["GET"])
def get_agenda_semana():
    return _pending("The parliamentary agenda is not in the parlamento-aberto release yet.", "S13")


# Temporary: removed in the master merge that brings S5, S6 and S7.


@pending_bp.route("/deputados/<int:cad_id>/detalhes", methods=["GET"])
def get_deputado_detalhes(cad_id):
    return _pending("Deputy details move to the DuckDB layer in S5.", "S5")


@pending_bp.route("/deputados/<int:cad_id>/atividades", methods=["GET"])
def get_deputado_atividades(cad_id):
    return _pending("Deputy activities move to the DuckDB layer in S5.", "S5")


@pending_bp.route("/deputados/<int:cad_id>/conflitos-interesse", methods=["GET"])
def get_deputado_conflitos_interesse(cad_id):
    return _pending("The interest register moves to the DuckDB layer in S5.", "S5")


@pending_bp.route("/deputados/<int:cad_id>/voting-analytics", methods=["GET"])
def get_deputado_voting_analytics(cad_id):
    return _pending("Deputy voting analytics move to the DuckDB layer in S6.", "S6")


@pending_bp.route("/partidos/<path:partido_sigla>/voting-analytics", methods=["GET"])
def get_partido_voting_analytics(partido_sigla):
    return _pending("Party voting analytics move to the DuckDB layer in S6.", "S6")


@pending_bp.route("/partidos/<path:partido_sigla>/deputados", methods=["GET"])
def get_partido_deputados(partido_sigla):
    return _pending("The party deputies list moves to the DuckDB layer in S7.", "S7")
