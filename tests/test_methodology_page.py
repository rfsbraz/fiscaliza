"""The methodology page, /metodologia (#113, second half)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
APP = SRC / "App.jsx"
PAGE = SRC / "components" / "Metodologia.jsx"
CONTENT = SRC / "content" / "metodologia.md"
REDIRECTS = ROOT / "deploy" / "_redirects"
COVERAGE = (
    "Mesmo nesse período, os ficheiros da AR só incluem as pessoas que constam das listas da XVII Legislatura,"
    " incluindo suplentes. Quem já não está nessas listas não tem declaração nos dados abertos, mesmo que a"
    " tenha entregue na altura. Os dados têm declaração para {com_declaracao} de {total} deputados com mandato"
    " da XI à XV Legislatura."
)
FORM = "https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml"

SECTIONS = [
    "Fontes e licença",
    "Data dos dados",
    "Presenças no Plenário",
    "Taxa de aprovação de iniciativas",
    "Sentido de voto",
    "Intervenções",
    "Declarações de interesses",
    "Eleitos, em exercício e mandatos suspensos",
    "I Legislatura: I-A e I-B",
    "Sessões plenárias",
    "Lacunas conhecidas",
    "Reportar um erro nos dados",
]


def test_route_footer_link_and_rewrite():
    app = APP.read_text()
    route = app.index('<Route path="/metodologia" element={<Metodologia />} />')
    assert route < app.index('<Route path="*" element={<NotFound />} />')
    assert 'to="/metodologia"' in app
    assert "Metodologia e fontes" in app
    assert "/metodologia / 200" in REDIRECTS.read_text().splitlines()


def test_content_has_the_reviewed_sections_in_order():
    text = CONTENT.read_text()
    assert text.startswith("# Metodologia e fontes\n")
    assert re.findall(r"^## (.+)$", text, flags=re.M) == SECTIONS


def test_content_has_no_reviewer_notes():
    text = CONTENT.read_text()
    assert "<!--" not in text and "VERIFICAR" not in text and "Reviewer" not in text
    # The seated count is dated to the data, as on the site (#125).
    assert "com lugar na data dos dados" in text and "com lugar hoje" not in text
    # Only the placeholders the page fills in.
    assert set(re.findall(r"\{(\w+)\}", text)) == {"source_updated", "tag", "n", "com_declaracao", "total"}


def test_declaration_coverage_line_as_confirmed():
    text = CONTENT.read_text()
    assert COVERAGE in text
    # The coverage line now says precisely who is missing, so the vaguer phrases go.
    assert "e só de parte deles" not in text
    assert "e só para parte dos deputados" not in text
    assert "- **Declarações de interesses:** só da XI à XV nos dados abertos da AR. A XVI" in text


def test_errors_go_to_the_correction_form_with_no_contact_address():
    text = CONTENT.read_text()
    assert FORM in text
    assert "erros no próprio site" in text
    assert "@" not in text and "mailto:" not in text
    assert "mailto:" not in PAGE.read_text()


def test_page_reads_the_data_date_tag_and_interventions_and_is_indexable():
    page = PAGE.read_text()
    assert "apiFetch('health')" in page
    assert "source_updated" in page and "tag" in page
    assert "apiFetch('legislaturas')" in page and "intervencoes_publicadas" in page
    assert "cobertura_declaracoes" in page and "com_declaracao" in page
    assert "metodologia.md?raw" in page
    assert "noindex" not in page and "robots" not in page
