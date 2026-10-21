"""Fiscaliza API: Flask over the read-only DuckDB file that `python -m fiscaliza_data sync` builds.

The frontend and the API share one origin (/api), so there is no CORS. Logs go to stderr only.
"""

import logging
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.data.connection import init_app as init_data
from app.routes.activity import activity_bp
from app.routes.core import core_bp
from app.routes.deputies import deputies_bp
from app.routes.health import health_bp
from app.routes.parties import parties_bp
from app.routes.pending import pending_bp

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("fiscaliza")

app = Flask(__name__)
app.debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

app.register_blueprint(core_bp, url_prefix="/api")
app.register_blueprint(deputies_bp, url_prefix="/api")
app.register_blueprint(parties_bp, url_prefix="/api")
app.register_blueprint(activity_bp, url_prefix="/api")
app.register_blueprint(health_bp, url_prefix="/api")
# Last, so a real route always wins over a pending stub while they overlap.
app.register_blueprint(pending_bp, url_prefix="/api")

# Site data: the read-only DuckDB file built by `python -m fiscaliza_data sync`.
init_data(app)


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({"error": e.name, "message": e.description, "code": e.code}), e.code


@app.errorhandler(Exception)
def handle_exception(e):
    log.exception("unhandled error")
    return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def api_root():
    return jsonify({"service": "fiscaliza-api", "health": "/api/health"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
