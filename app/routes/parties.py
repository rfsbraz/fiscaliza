"""Party page routes on the DuckDB data layer (S7)."""

from flask import Blueprint, request

from app.data.connection import DataUnavailable
from app.routes.core import _not_found, _serve, _unavailable
from app.services import parties
from app.services.core import NotFound

parties_bp = Blueprint("parties", __name__)
parties_bp.register_error_handler(NotFound, _not_found)
parties_bp.register_error_handler(DataUnavailable, _unavailable)


@parties_bp.route("/partidos/<path:partido_sigla>/deputados", methods=["GET"])
def get_partido_deputados(partido_sigla):
    return _serve(parties.partido_deputados, partido_sigla, request.args.get("legislatura") or None)
