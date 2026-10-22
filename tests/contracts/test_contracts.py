"""Contract tests for the API endpoints the frontend uses.

One contract per endpoint lives in ``endpoints/*.json``: the key paths the React
components read, their type and nullability, and the component line that reads each
one. Fields removed by the approved drops are listed under ``dropped`` with the reason,
and are not part of the contract.
"""

import json
import re
from pathlib import Path

import pytest

from tests.contracts.checker import _TYPES, check
from tests.contracts.services import PORTED

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = Path(__file__).resolve().parent / "endpoints"
CONTRACTS = {p.stem: json.loads(p.read_text()) for p in sorted(CONTRACT_DIR.glob("*.json"))}
FRONTEND = ROOT / "frontend" / "src"
ROUTES = ROOT / "app" / "routes"


def _endpoint_regex(endpoint):
    return re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(endpoint)) + "$")


def _frontend_calls():
    """Endpoints passed to apiFetch in the frontend, placeholders as {}, query dropped."""
    calls = set()
    for path in FRONTEND.rglob("*.js*"):
        for literal in re.findall(r"apiFetch\(\s*[`'\"]([^`'\"]+)[`'\"]", path.read_text()):
            literal = re.sub(r"\$\{[^}]*\}", "{}", literal).split("?", 1)[0].strip("/")
            calls.add(literal)
    return calls


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_endpoint_matches_contract(name, contract_data_source):
    contract = CONTRACTS[name]
    if name not in PORTED:
        pytest.xfail(f"{contract['endpoint']} is not ported to the new data layer yet")
    payload = PORTED[name](contract_data_source)
    assert check(payload, contract) == []


def test_every_frontend_call_has_a_contract():
    patterns = {name: _endpoint_regex(c["endpoint"]) for name, c in CONTRACTS.items()}
    calls = _frontend_calls()
    assert calls, "found no apiFetch calls in frontend/src"
    unmatched = sorted(call for call in calls if not any(p.match(call) for p in patterns.values()))
    unused = sorted(name for name, p in patterns.items() if not any(p.match(call) for call in calls))
    assert unmatched == [], "frontend calls with no contract"
    assert unused == [], "contracts no frontend code calls"


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_contract_route_exists(name):
    route = CONTRACTS[name]["route"].removeprefix("/api")
    sources = "".join(p.read_text() for p in ROUTES.glob("*.py"))
    assert f".route('{route}'" in sources or f'.route("{route}"' in sources


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_contract_keys_cite_the_component_line_that_reads_them(name):
    problems = []
    for key in CONTRACTS[name]["keys"]:
        assert key["type"] in _TYPES, key
        assert isinstance(key["nullable"], bool), key
        file, line = key["read_at"].rsplit(":", 1)
        lines = (ROOT / file).read_text().split("\n")
        last = re.findall(r"[^.\[\]]+", key["path"])[-1]
        if not re.search(rf"\b{re.escape(last)}\b", lines[int(line) - 1]):
            problems.append(f"{key['path']}: {key['read_at']} does not read {last}")
    assert problems == []


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_dropped_fields_are_not_in_the_contract(name):
    contract = CONTRACTS[name]
    for dropped in contract["dropped"]:
        assert dropped["reason"]
        prefix = dropped["path"]
        clash = [
            k["path"]
            for k in contract["keys"]
            if k["path"] == prefix or k["path"].startswith((prefix + ".", prefix + "[]"))
        ]
        assert clash == []


def test_approved_drops_are_recorded():
    dropped = {(name, d["path"]) for name, c in CONTRACTS.items() for d in c["dropped"]}
    assert ("deputado_detalhes", "estatisticas.contexto_oposicao") in dropped
    for field in ("spouse_name", "spouse_deputy", "marital_status", "matrimonial_regime", "dgf_number"):
        assert ("deputado_conflitos_interesse", field) in dropped
    assert ("deputado_voting_analytics", "theme_analysis") in dropped
    assert ("deputado_voting_analytics", "data_sources.budget_votes") in dropped
    assert ("partido_voting_analytics", "ideological_positioning") in dropped


def test_there_is_one_contract_per_frontend_endpoint():
    assert len(CONTRACTS) == 22
