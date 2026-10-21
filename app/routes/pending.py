"""Endpoints the frontend calls whose data is not on the DuckDB layer yet.

Each answers 503 with a short reason and the step that brings it back. The frontend reads any
non-2xx answer as "not available" and shows its notice, so the page keeps working. None of
these touch the data file.

Permanent until their mart is released:
- attendance (F12) waits on the plenary attendance mart, S11;
- the agenda for today and this week (F32) waits on the agenda mart, S13.

Temporary, only until S6 (#79) merges and registers the real routes: the deputy and party
voting analytics. tests/test_pending_endpoints.py fails on a route registered twice, so these
stubs go in the master merge that brings S6.
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


# Temporary: removed in the master merge that brings S6.


@pending_bp.route("/deputados/<int:cad_id>/voting-analytics", methods=["GET"])
def get_deputado_voting_analytics(cad_id):
    return _pending("Deputy voting analytics move to the DuckDB layer in S6.", "S6")


@pending_bp.route("/partidos/<path:partido_sigla>/voting-analytics", methods=["GET"])
def get_partido_voting_analytics(partido_sigla):
    return _pending("Party voting analytics move to the DuckDB layer in S6.", "S6")
