"""The site loads nothing from a font CDN, and the frontend's metadata and dev config are clean.

Fonts are self-hosted under frontend/src/assets/fonts, each family with its licence, so a
visit sends no request to Google or any other third party.
"""

import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
FONTS = FRONTEND / "src" / "assets" / "fonts"
CDN = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|fonts\.bunny\.net|use\.typekit\.net|cdnjs|jsdelivr|unpkg")
FAMILIES = ["libre-baskerville", "source-sans-3", "jetbrains-mono"]


def _sources():
    yield FRONTEND / "index.html"
    for path in (FRONTEND / "src").rglob("*"):
        if path.suffix in {".js", ".jsx", ".css", ".html"}:
            yield path


def test_no_font_or_asset_cdn_anywhere_in_the_frontend():
    found = [str(p.relative_to(ROOT)) for p in _sources() if CDN.search(p.read_text(encoding="utf-8"))]
    assert found == []


def test_the_font_stylesheet_is_imported_by_the_app():
    assert "import './assets/fonts/fonts.css'" in (FRONTEND / "src" / "main.jsx").read_text()


def test_every_font_face_points_at_a_committed_woff2():
    css = (FONTS / "fonts.css").read_text()
    urls = re.findall(r"url\(([^)]+)\)", css)
    assert urls
    for url in urls:
        assert url.startswith("./") and url.endswith(".woff2"), url
        assert (FONTS / url).is_file(), url
    # Nothing committed that the stylesheet doesn't use.
    used = {(FONTS / u).resolve() for u in urls}
    assert {p.resolve() for p in FONTS.rglob("*.woff2")} == used


@pytest.mark.parametrize("family", FAMILIES)
def test_each_family_ships_its_open_font_licence(family):
    licence = (FONTS / family / "OFL.txt").read_text()
    assert "SIL OPEN FONT LICENSE Version 1.1" in licence


def test_the_font_families_the_css_names_are_all_self_hosted():
    css = (FONTS / "fonts.css").read_text()
    hosted = set(re.findall(r"font-family: '([^']+)'", css))
    assert hosted == {"Libre Baskerville", "Source Sans 3", "JetBrains Mono"}


def test_no_ngrok_host_in_the_vite_config():
    assert "ngrok" not in (FRONTEND / "vite.config.js").read_text()


def test_frontend_package_licence_matches_the_project():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["license"]
    assert json.loads((FRONTEND / "package.json").read_text()).get("license") == project


def test_the_build_never_inlines_a_font_as_a_data_uri():
    # font-src is 'self' only, so a font Vite inlined as data: would be blocked by the CSP.
    config = (FRONTEND / "vite.config.js").read_text()
    assert re.search(r"assetsInlineLimit: \(file\) => \(file\.endsWith\('\.woff2'\) \? false : undefined\)", config)
