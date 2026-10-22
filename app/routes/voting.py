"""Voting analytics for the deputy and party pages on the DuckDB data layer. Each route
parses its arguments, calls a service and returns JSON."""

from flask import Blueprint, current_app, jsonify, request

from app.data.connection import DataUnavailable, data_source
from app.services import voting
from app.services.core import NotFound

voting_bp = Blueprint("voting", __name__)


def _serve(service, *args, **kwargs):
    with data_source(current_app).cursor() as con:
        return jsonify(service(con, *args, **kwargs))


@voting_bp.errorhandler(NotFound)
def _not_found(e):
    return jsonify({"error": str(e)}), 404


@voting_bp.errorhandler(DataUnavailable)
def _unavailable(e):
    current_app.logger.error("data unavailable: %s", e)
    return jsonify({"error": "Dados indisponíveis"}), 503


@voting_bp.route("/deputados/<int:cad_id>/voting-analytics", methods=["GET"])
def get_deputado_voting_analytics(cad_id):
    return _serve(voting.deputado_voting_analytics, cad_id, request.args.get("legislatura") or None)


@voting_bp.route("/partidos/<path:partido_sigla>/voting-analytics", methods=["GET"])
def get_partido_voting_analytics(partido_sigla):
    return _serve(voting.partido_voting_analytics, partido_sigla, request.args.get("legislatura") or None)
