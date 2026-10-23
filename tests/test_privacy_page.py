"""The privacy note, /privacidade (#220)."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
APP = SRC / "App.jsx"
PAGE = SRC / "components" / "Privacidade.jsx"
CONTENT = SRC / "content" / "privacidade.md"
spec = importlib.util.spec_from_file_location("pages", ROOT / "deploy" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)
# The public email on github.com/rfsbraz, the contact in CODE_OF_CONDUCT.md.
CONTACT = "rfsbraz@gmail.com"


def test_route_footer_link_and_page():
    app = APP.read_text()
    route = app.index('<Route path="/privacidade" element={<Privacidade />} />')
    assert route < app.index('<Route path="*" element={<NotFound />} />')
    assert 'to="/privacidade"' in app
    # deploy/pages.py writes privacidade.html with its own head, and the sitemap lists it.
    assert pages.STATIC_ROUTES["/privacidade"][0] == "Privacidade"


def test_content_is_the_reviewed_note_with_the_contact():
    text = CONTENT.read_text()
    assert text.startswith("## Privacidade\n")
    assert re.findall(r"^\*\*([^*]+)\*\*", text, flags=re.M) == [
        "Contagem de visitas.",
        "Erros.",
        "Alojamento.",
        "Tipos de letra.",
    ]
    assert "Cloudflare Web Analytics" in text and "Sentry" in text
    assert "a definir" not in text and "[" not in text
    assert text.rstrip().endswith(f"Dúvidas: {CONTACT}")


def test_page_renders_the_note_and_is_indexable():
    page = PAGE.read_text()
    assert "privacidade.md?raw" in page
    assert "Privacidade · Fiscaliza" in page
    assert "noindex" not in page and "robots" not in page
