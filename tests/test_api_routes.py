"""The API serves exactly the endpoints the frontend calls, plus health checks.

The dead features (Transparency page, admin dashboard and the endpoints nothing
calls) are gone, so the route table is pinned here.
"""

import pytest

FRONTEND_ENDPOINTS = {
    "/api/legislaturas",
    "/api/estatisticas",
    "/api/deputados",
    "/api/deputados/<int:cad_id>/detalhes",
    "/api/deputados/<int:cad_id>/atividades",
    "/api/deputados/<int:cad_id>/conflitos-interesse",
    "/api/deputados/<int:cad_id>/attendance",
    "/api/deputados/<int:cad_id>/voting-analytics",
    "/api/partidos",
    "/api/partidos/<path:partido_sigla>/deputados",
    "/api/partidos/<path:partido_sigla>/voting-analytics",
    "/api/coligacoes",
    "/api/coligacoes/<path:coligacao_sigla>",
    "/api/coligacoes/<path:coligacao_sigla>/deputados",
    "/api/coligacoes/<path:coligacao_sigla>/partidos",
    "/api/agenda/hoje",
    "/api/agenda/semana",
    "/api/votacoes/recentes",
    "/api/estatisticas/atividade",
}
HEALTH_ENDPOINTS = {"/api/health", "/api/ready", "/api/ping"}

REMOVED = [
    "/api/test",
    "/api/deputados/1",
    "/api/partidos/1",
    "/api/circulos",
    "/api/search",
    "/api/partidos/PS/votacoes",
    "/api/feed/atividades",
    "/api/feed/atividades/iniciativa/1/participantes",
    "/api/deputados/1/biografia",
    "/api/deputados/by-name/Nome",
    "/api/deputados/1/votacoes",
    "/api/votacoes",
    "/api/votacoes/1",
    "/api/entidades-politicas/search",
    "/api/entidades-politicas/statistics",
    "/api/transparency/live-activity",
    "/api/transparency/legislative-progress",
    "/api/transparency/deputy-performance",
    "/api/transparency/accountability-metrics",
    "/api/transparency/citizen-participation",
    "/api/admin/import-stats",
    "/api/admin/import-status",
    "/api/admin/recent-errors",
]


def test_api_routes_are_the_frontend_endpoints_and_health_checks(app):
    routes = {rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/api/")}
    assert routes == FRONTEND_ENDPOINTS | HEALTH_ENDPOINTS


@pytest.mark.parametrize("path", REMOVED)
def test_removed_endpoint_is_not_routed(app, path):
    adapter = app.url_map.bind("localhost")
    with pytest.raises(Exception) as excinfo:
        adapter.match(path, method="GET")
    assert getattr(excinfo.value, "code", None) == 404
