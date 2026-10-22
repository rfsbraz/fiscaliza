"""Deputy page on the DuckDB data layer: details, activities, interest register and attendance. Each route
parses its arguments, calls a service and returns JSON."""

from flask import Blueprint, current_app, jsonify, request

from app.data.connection import DataUnavailable, data_source
from app.services import attendance, core, deputies

deputies_bp = Blueprint("deputies", __name__)


def _serve(service, *args, **kwargs):
    with data_source(current_app).cursor() as con:
        return jsonify(service(con, *args, **kwargs))


@deputies_bp.errorhandler(core.NotFound)
def _not_found(e):
    return jsonify({"error": str(e)}), 404


@deputies_bp.errorhandler(DataUnavailable)
def _unavailable(e):
    current_app.logger.error("data unavailable: %s", e)
    return jsonify({"error": "Dados indisponíveis"}), 503


@deputies_bp.route("/deputados/<int:cad_id>/detalhes", methods=["GET"])
def get_deputado_detalhes(cad_id):
    return _serve(deputies.detalhes, cad_id)


@deputies_bp.route("/deputados/<int:cad_id>/atividades", methods=["GET"])
def get_deputado_atividades(cad_id):
    return _serve(
        deputies.atividades,
        cad_id,
        legislatura=request.args.get("legislatura") or None,
        tipo=request.args.get("tipo_intervencao") or None,
        ordem=request.args.get("ordenacao_intervencoes") or "newest",
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 50, type=int),
    )


@deputies_bp.route("/deputados/<int:cad_id>/conflitos-interesse", methods=["GET"])
def get_deputado_conflitos_interesse(cad_id):
    return _serve(deputies.conflitos_interesse, cad_id)


@deputies_bp.route("/deputados/<int:cad_id>/attendance", methods=["GET"])
def get_deputado_attendance(cad_id):
    return _serve(attendance.deputado_attendance, cad_id)
