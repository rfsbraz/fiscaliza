"""Endpoints whose mart is not released yet answer 503 with a reason, never a crash.

Attendance (F12) waits on the plenary attendance mart (S11) and the agenda for today and
the week (F32) on the agenda mart (S13). The frontend reads a non-2xx answer as "not
available" and shows its notice. These routes must not need a data file at all.
"""

import pytest

PENDING = {
    "/api/deputados/123/attendance": "S11",
    "/api/agenda/hoje": "S13",
    "/api/agenda/semana": "S13",
}


@pytest.mark.parametrize("path", sorted(PENDING))
def test_pending_endpoint_answers_503_with_a_reason(client, path):
    response = client.get(path)
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "not_available"
    assert body["reason"]
    assert body["planned"] == PENDING[path]


def test_each_route_is_registered_once(app):
    # A route served twice means a pending stub shadows (or is shadowed by) the real endpoint.
    rules = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/api/")]
    assert sorted({r for r in rules if rules.count(r) > 1}) == []


def test_app_has_no_cors_or_sqlalchemy(app, client):
    # Same origin since S9, and no database server any more.
    assert "sqlalchemy" not in app.extensions
    response = client.get("/api/ping", headers={"Origin": "https://example.invalid"})
    assert "Access-Control-Allow-Origin" not in response.headers
