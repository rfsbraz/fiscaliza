"""S9: the AR attribution line on every page, and the frontend calling /api on its own origin.

The AR terms and Lei n.º 26/2016, art. 19.º, n.º 5 ask for the source and the date of the
last update; the parlamento-aberto marts are CC BY 4.0.
"""

import re
from pathlib import Path

import duckdb
import pytest

from app.services import core
from tests.site_data import TAG, build_site_data

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
FOOTER = FRONTEND / "src" / "components" / "DataAttribution.jsx"
AR_LINE = "Fonte: Assembleia da República, dados abertos, atualizados a "


def test_footer_has_the_ar_attribution_line_with_source_updated():
    source = FOOTER.read_text()
    assert AR_LINE + "${sourceUpdated}." in source
    assert "source_updated" in source and "tag" in source
    assert "CC BY 4.0" in source and "parlamento-aberto" in source


def test_footer_reads_the_live_release_from_health():
    assert re.search(r"apiFetch\(\s*['\"]health['\"]", FOOTER.read_text())


def test_footer_is_on_every_page():
    app = (FRONTEND / "src" / "App.jsx").read_text()
    assert "import DataAttribution from './components/DataAttribution'" in app
    footer = app[app.index("<footer") : app.index("</footer>")]
    assert "<DataAttribution" in footer
    assert app.index("</Routes>") < app.index("<footer")


def test_no_site_wide_note_that_the_data_is_demonstrative():
    # The data is the real AR release now, so the "Nota Editorial" strip under the nav goes.
    app = (FRONTEND / "src" / "App.jsx").read_text()
    assert "Nota Editorial" not in app
    assert "demonstrativos" not in app
    assert "showBanner" not in app


def test_frontend_calls_the_api_on_its_own_origin():
    api = (FRONTEND / "src" / "config" / "api.js").read_text()
    assert "import.meta.env.VITE_API_BASE_URL || '/api'" in api
    env = (FRONTEND / ".env.production").read_text().split()
    assert env == ["VITE_API_BASE_URL=/api"]
    hits = [str(p) for p in (FRONTEND / "src").rglob("*.js*") if "api.fiscaliza.pt" in p.read_text()]
    assert hits == []


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    data_dir = build_site_data(tmp_path_factory.mktemp("site"))
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def test_health_payload_has_the_tag_and_source_updated_as_text(con):
    body = core.health(con)
    assert body["status"] == "healthy"
    assert body["data"]["tag"] == TAG
    assert body["data"]["source_updated"] == "2026-10-20"
