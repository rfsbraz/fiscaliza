"""Endpoints the frontend calls whose data is not on the DuckDB layer yet.

Each answers 503 with a short reason and the step that brings it back. The frontend reads any
non-2xx answer as "not available" and shows its notice, so the page keeps working. None of
these touch the data file.

Permanent until their mart is released:
- the agenda for today and this week (F32) waits on the agenda mart, S13.

tests/test_pending_endpoints.py fails on a route registered twice, so a stub goes in the
master merge that brings its real route.
"""

from flask import Blueprint, jsonify

pending_bp = Blueprint("pending", __name__)

# The page shows this; frontend/src/config/staticApi.js gives the same reason.
AGENDA_REASON = "A agenda parlamentar ainda não está na release do parlamento-aberto."


def _pending(reason, planned):
    return jsonify({"status": "not_available", "reason": reason, "planned": planned}), 503


@pending_bp.route("/agenda/hoje", methods=["GET"])
def get_agenda_hoje():
    return _pending(AGENDA_REASON, "S13")


@pending_bp.route("/agenda/semana", methods=["GET"])
def get_agenda_semana():
    return _pending(AGENDA_REASON, "S13")
