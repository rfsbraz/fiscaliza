"""Agenda page routes on the DuckDB data layer (S8): recent votes and activity stats."""

from flask import Blueprint, request

from app.data.connection import DataUnavailable
from app.routes.core import _not_found, _serve, _unavailable
from app.services import activity
from app.services.core import NotFound

activity_bp = Blueprint("activity", __name__)
activity_bp.register_error_handler(NotFound, _not_found)
activity_bp.register_error_handler(DataUnavailable, _unavailable)


@activity_bp.route("/votacoes/recentes", methods=["GET"])
def get_votacoes_recentes():
    return _serve(
        activity.votacoes_recentes,
        limite=request.args.get("limite", activity.DEFAULT_LIMIT, type=int),
        legislatura=request.args.get("legislatura") or None,
    )


@activity_bp.route("/estatisticas/atividade", methods=["GET"])
def get_estatisticas_atividade():
    return _serve(activity.estatisticas_atividade)
