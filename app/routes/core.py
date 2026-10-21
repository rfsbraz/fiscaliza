"""Core pages on the DuckDB data layer: legislatures, dashboard statistics, deputies,
parties and coalitions. Each route parses its arguments, calls a service and returns JSON."""

from flask import Blueprint, current_app, jsonify, request

from app.data.connection import DataUnavailable, data_source
from app.services import core

core_bp = Blueprint("core", __name__)


def _flag(name, default):
    return request.args.get(name, default).lower() == "true"


def _serve(service, *args, **kwargs):
    with data_source(current_app).cursor() as con:
        return jsonify(service(con, *args, **kwargs))


@core_bp.errorhandler(core.NotFound)
def _not_found(e):
    return jsonify({"error": str(e)}), 404


@core_bp.errorhandler(DataUnavailable)
def _unavailable(e):
    current_app.logger.error("data unavailable: %s", e)
    return jsonify({"error": "Data not available"}), 503


@core_bp.route("/legislaturas", methods=["GET"])
def get_legislaturas():
    return _serve(core.legislaturas)


@core_bp.route("/estatisticas", methods=["GET"])
def get_estatisticas():
    return _serve(core.estatisticas, request.args.get("legislatura") or None)


@core_bp.route("/deputados", methods=["GET"])
def get_deputados():
    return _serve(
        core.deputados,
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 20, type=int),
        search=request.args.get("search") or None,
        legislatura=request.args.get("legislatura") or None,
        active_only=_flag("active_only", "true"),
    )


@core_bp.route("/partidos", methods=["GET"])
def get_partidos():
    return _serve(core.partidos, request.args.get("legislatura") or None, active_only=_flag("active_only", "true"))


@core_bp.route("/coligacoes", methods=["GET"])
def get_coligacoes():
    return _serve(core.coligacoes, include_inactive=_flag("include_inactive", "false"))


@core_bp.route("/coligacoes/<path:coligacao_sigla>", methods=["GET"])
def get_coligacao(coligacao_sigla):
    return _serve(core.coligacao, coligacao_sigla)


@core_bp.route("/coligacoes/<path:coligacao_sigla>/deputados", methods=["GET"])
def get_coligacao_deputados(coligacao_sigla):
    return _serve(core.coligacao_deputados, coligacao_sigla, request.args.get("legislatura") or None)


@core_bp.route("/coligacoes/<path:coligacao_sigla>/partidos", methods=["GET"])
def get_coligacao_partidos(coligacao_sigla):
    return _serve(core.coligacao_partidos, coligacao_sigla)
