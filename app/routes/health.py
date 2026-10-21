"""Health checks on the DuckDB data layer (F42).

/api/ping never touches the data. /api/health shows the live release tag and
source_updated, or 503 when there is no data file. /api/ready is 200 only when the current
legislature has seated deputies.
"""

from flask import Blueprint, current_app, jsonify

from app.data import repository
from app.data.connection import DataUnavailable, data_source

health_bp = Blueprint("health", __name__)
SERVICE = "fiscaliza-api"


@health_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "pong", "service": SERVICE}), 200


@health_bp.route("/health", methods=["GET"])
def health_check():
    try:
        with data_source(current_app).cursor() as con:
            meta = repository.meta(con)
    except DataUnavailable as e:
        return jsonify({"status": "unhealthy", "service": SERVICE, "reason": str(e)}), 503
    data = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in (meta or {}).items()}
    return jsonify({"status": "healthy", "service": SERVICE, "data": data}), 200


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    try:
        with data_source(current_app).cursor() as con:
            leg = repository.current_legislature(con)
            seats = repository.seats_by_group(con, leg["legislature"], leg["ref_day"]) if leg else []
    except DataUnavailable as e:
        return jsonify({"status": "not_ready", "reason": str(e)}), 503
    seated = sum(g["seats"] for g in seats)
    if not seated:
        return jsonify({"status": "not_ready", "reason": "no seated deputies in the current legislature"}), 503
    return jsonify({"status": "ready", "legislature": leg["legislature"], "seated": seated}), 200
