"""Text a reader can see is pt-PT: API reasons and errors, thrown frontend errors, labels and lang.

Console-only logs, comments and identifiers stay English.
"""

import re
from pathlib import Path

import pytest

from app.data.connection import DataUnavailable

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
AGENDA_REASON = "A agenda parlamentar ainda não está na release do parlamento-aberto."


@pytest.mark.parametrize("path", ["/api/agenda/hoje", "/api/agenda/semana"])
def test_pending_reason_is_pt_pt(client, path):
    assert client.get(path).get_json()["reason"] == AGENDA_REASON


def test_static_client_gives_the_same_pending_reason():
    assert AGENDA_REASON in (FRONTEND / "src" / "config" / "staticApi.js").read_text()


def test_unknown_api_path_answers_in_pt_pt(client):
    body = client.get("/api/caminho-que-nao-existe").get_json()
    assert body == {"error": "Não encontrado", "message": "O endereço pedido não existe.", "code": 404}


def test_unhandled_error_answers_in_pt_pt(app):
    from app.main import handle_exception

    with app.test_request_context():
        response, status = handle_exception(RuntimeError("boom"))
    assert status == 500
    assert response.get_json() == {"error": "Erro interno do servidor"}


@pytest.mark.parametrize("module", ["core", "deputies", "voting"])
def test_data_unavailable_answers_in_pt_pt(app, module):
    routes = __import__(f"app.routes.{module}", fromlist=["_unavailable"])
    with app.test_request_context():
        response, status = routes._unavailable(DataUnavailable("no data file"))
    assert status == 503
    assert response.get_json() == {"error": "Dados indisponíveis"}


def test_not_found_messages_in_the_services_are_pt_pt():
    english = []
    for path in sorted((ROOT / "app" / "services").glob("*.py")):
        for message in re.findall(r"raise NotFound\((f?[\"'].*?[\"'])", path.read_text()):
            if re.search(r"\bnot found\b|\bno legislature\b|\bheld no seat\b", message):
                english.append(f"{path.name}: {message}")
    assert english == []


ENGLISH_IN_THE_UI = [
    "API request failed",
    "HTTP error!",
    "Invalid JSON response",
    "error: 'Not found'",
    "is not in the parlamento-aberto release",
    "Total carreira",
    "Total Analisado",
    "${response.statusText}",
    "${deputyResponse.statusText}",
    "'N/A'",
    '"N/A"',
    ">N/A<",
]


def test_no_english_reader_facing_string_in_the_frontend():
    found = []
    for path in sorted((FRONTEND / "src").rglob("*.js*")):
        if path.name.endswith(".test.js"):
            continue
        text = path.read_text(encoding="utf-8")
        found += [f"{path.relative_to(FRONTEND)}: {s}" for s in ENGLISH_IN_THE_UI if s in text]
    assert found == []


def test_the_page_is_pt_pt():
    html = (FRONTEND / "index.html").read_text()
    assert '<html lang="pt-PT">' in html
    assert '<meta property="og:locale" content="pt_PT" />' in html


@pytest.mark.parametrize(
    "doc, heading", [("docs/STATIC_EXPORT.md", "# Exportação estática"), ("tests/contracts/README.md", "# Contratos")]
)
def test_developer_docs_are_pt_pt(doc, heading):
    assert (ROOT / doc).read_text().startswith(heading)
