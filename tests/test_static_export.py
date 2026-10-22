"""Static export (#90): the site API rendered to JSON files that any static host can serve.

The contract: for every request the frontend makes, the answer the browser builds from the
static files (frontend/src/config/staticApi.js, run here with node) equals what the Flask
endpoint returns for the same request on the synthetic release in tests/site_data.py.
Endpoints whose route is still on the old code, or a 503 stub, are expected to answer "not
available" from the static files too.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from fiscaliza_data import export
from tests.site_data import build_site_data

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
ANSWERS = FRONTEND / "scripts" / "static-answers.mjs"
# Routes on these blueprints are not on the DuckDB layer (old code or 503 stubs).
NOT_ON_DUCKDB = {"parlamento", "agenda", "pending"}
# One file each, with the endpoint it holds.
FLAT = {
    "legislaturas.json": "legislaturas",
    "estatisticas.json": "estatisticas",
    "partidos.json": "partidos",
    "coligacoes.json": "coligacoes?include_inactive=false",
    "coligacoes-todas.json": "coligacoes?include_inactive=true",
    "coligacoes/ad.json": "coligacoes/AD",
    "coligacoes/ad/deputados.json": "coligacoes/AD/deputados",
    "coligacoes/ad/partidos.json": "coligacoes/AD/partidos",
    "votacoes/recentes/5.json": "votacoes/recentes?limite=5",
    "votacoes/recentes/10.json": "votacoes/recentes",
    "estatisticas/atividade.json": "estatisticas/atividade",
    "health.json": "health",
}


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture(scope="module")
def out(data_dir, tmp_path_factory):
    target = tmp_path_factory.mktemp("static") / "api"
    export.export(data_dir, target, jobs=1)
    return target


@pytest.fixture(scope="module")
def flask_app(data_dir):
    from app.data.connection import EXTENSION, init_app
    from app.main import app

    before = app.extensions.get(EXTENSION)
    app.config["TESTING"] = True
    init_app(app, data_dir)
    yield app
    if before is None:
        app.extensions.pop(EXTENSION, None)
    else:
        app.extensions[EXTENSION] = before


@pytest.fixture(scope="module")
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture(scope="module")
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def _files(out):
    return sorted(p for p in out.rglob("*") if p.is_file())


def _on_duckdb(flask_app, endpoint):
    path = "/api/" + endpoint.split("?")[0]
    name, _ = flask_app.url_map.bind("localhost").match(path)
    return name.split(".")[0] not in NOT_ON_DUCKDB


# Path scheme


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PàF", "paf"),
        ("MDP/CDE", "mdp-cde"),
        ("CDS-PP", "cds-pp"),
        ("PPD/PSD", "ppd-psd"),
        ("XVII", "xvii"),
        ("Constituinte", "constituinte"),
        ("  Ação  Nova ", "acao-nova"),
    ],
)
def test_one_path_form_for_legislatures_parties_and_coalitions(value, expected):
    assert export.slug(value) == expected


def test_two_names_with_the_same_path_are_refused():
    with pytest.raises(export.ExportError, match="same path"):
        export.slugs(["MDP/CDE", "MDP-CDE"])


# Files and limits


def test_flat_files_equal_the_flask_answers(out, client):
    for path, endpoint in FLAT.items():
        answer = client.get(f"/api/{endpoint}")
        assert answer.status_code == 200, endpoint
        assert json.loads((out / path).read_text()) == answer.get_json(), path


def test_deputy_search_index_holds_everyone_in_list_order(out, client):
    index = json.loads((out / "deputados.json").read_text())
    total = client.get("/api/deputados?active_only=false").get_json()["pagination"]["total"]
    assert len(index["deputados"]) == total
    first = client.get("/api/deputados?page=1&per_page=20&active_only=false").get_json()["deputados"]
    assert index["deputados"][:20] == first


def test_elected_people_who_never_sat_get_a_file(out):
    # #107: 501 was elected for XVII and never sat; 302 sat in XVI and is suspended in XVII.
    index = json.loads((out / "deputados.json").read_text())
    ids = [d["id_cadastro"] for d in index["deputados"]]
    assert 501 in ids and 500 not in ids
    assert index["registos"][ids.index(302)] == 2
    never = json.loads((out / "deputados" / "501.json").read_text())
    assert never["legislatura_atual"] == "XVII" and list(never["atividades"]) == ["XVII"]
    assert never["voting_analytics"] == {} and never["attendance"]["legislaturas"] == []
    suspended = json.loads((out / "deputados" / "302.json").read_text())
    assert suspended["legislatura_atual"] == "XVII" and list(suspended["atividades"]) == ["XVI", "XVII"]
    assert list(suspended["voting_analytics"]) == ["XVI"]


def test_render_stays_under_the_static_host_limits(out):
    assert export.MAX_FILES == 20_000
    assert export.MAX_FILE_BYTES == 25 * 1024 * 1024
    files = _files(out)
    assert 0 < len(files) < export.MAX_FILES
    assert max(p.stat().st_size for p in files) < export.MAX_FILE_BYTES


def test_one_file_per_deputy_not_per_deputy_and_legislature(out):
    # Everything about a deputy is one file, so the count grows with people, not with
    # people times legislatures (about 3,400 files on the real release instead of 20,000).
    assert not [p for p in _files(out) if re.match(r"deputados/\d+/", p.relative_to(out).as_posix())]


def test_too_many_files_fails_and_keeps_the_previous_output(data_dir, tmp_path, monkeypatch):
    target = tmp_path / "api"
    target.mkdir()
    (target / "legislaturas.json").write_text("{}")
    monkeypatch.setattr(export, "MAX_FILES", 3)
    with pytest.raises(export.ExportError, match="files"):
        export.export(data_dir, target, jobs=1)
    assert [p.name for p in target.iterdir()] == ["legislaturas.json"]
    assert [p.name for p in tmp_path.iterdir()] == ["api"]


def test_a_file_too_large_fails(data_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(export, "MAX_FILE_BYTES", 100)
    with pytest.raises(export.ExportError, match="bytes"):
        export.export(data_dir, tmp_path / "api", jobs=1)
    assert not (tmp_path / "api").exists()


def test_a_new_render_replaces_the_old_one(data_dir, tmp_path):
    target = tmp_path / "api"
    target.mkdir()
    (target / "stale.json").write_text("{}")
    result = export.export(data_dir, target, jobs=1)
    assert not (target / "stale.json").exists()
    assert result.files == len(_files(target))
    assert result.bytes == sum(p.stat().st_size for p in _files(target))


def test_cli_renders_and_reports(data_dir, tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "fiscaliza_data.export", "--data-dir", str(data_dir), "--out", str(tmp_path / "api")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert re.search(r"\d+ files", run.stdout)
    assert (tmp_path / "api" / "legislaturas.json").is_file()


def test_cli_fails_cleanly_without_data(tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "fiscaliza_data.export", "--data-dir", str(tmp_path), "--out", str(tmp_path / "api")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1
    assert "export failed" in run.stderr


# Same answers as Flask, through the browser code


def _requests(con, flask_app):
    """Every request shape the frontend makes, over the fixture's people, parties and
    coalitions, plus search, paging and interventions filters."""
    reqs = list(FLAT.values())
    reqs += [f"coligacoes/{c}{s}" for c in ("CDU", "FRS", "NOPE") for s in ("", "/deputados", "/partidos")]
    reqs += [
        "deputados?page=1&per_page=20&active_only=false",
        "deputados?page=2&per_page=20&active_only=false",
        "deputados?page=99&per_page=20&active_only=false",
        "deputados?page=1&per_page=500&active_only=false",
        "deputados?page=1&per_page=20&active_only=true",
        "deputados?page=1&per_page=20",
        "deputados?page=1&per_page=20&active_only=false&search=deputado%2012",
        "deputados?page=1&per_page=20&active_only=false&search=NOME%20completo%2023",
        "deputados?page=2&per_page=5&active_only=false&search=Profiss",
        "deputados?page=1&per_page=20&active_only=false&search=Deputádo%204",
        "deputados?page=1&per_page=20&active_only=false&search=nobody",
    ]
    people = [r[0] for r in con.execute("select distinct cadastro_id from deputy_elections order by 1").fetchall()]
    sample = sorted({*people[:3], *people[-3:], 1, 2, 90, 231, 232, 301, 302, 303, 501})
    legs = [r[0] for r in con.execute("select legislature from legislature_days").fetchall()]
    for cad in [*sample, 999999]:
        reqs += [f"deputados/{cad}/detalhes", f"deputados/{cad}/conflitos-interesse", f"deputados/{cad}/attendance"]
        reqs += [f"deputados/{cad}/voting-analytics"]
        reqs += [f"deputados/{cad}/voting-analytics?legislatura={leg}" for leg in legs]
        reqs += [f"deputados/{cad}/atividades?page=1&per_page=50"]
        # The page only offers the legislatures the person was elected or seated in; others are
        # not rendered.
        served = con.execute("select legislature from deputy_elections where cadastro_id = ?", [cad]).fetchall()
        for (leg,) in served:
            for tipo in ("", "interven", "Pergunta"):
                for order in ("newest", "oldest", "type"):
                    reqs.append(
                        f"deputados/{cad}/atividades?legislatura={leg}&tipo_intervencao={tipo}"
                        f"&ordenacao_intervencoes={order}&page=1&per_page=50"
                    )
            reqs.append(f"deputados/{cad}/atividades?legislatura={leg}&page=2&per_page=1")
    groups = [
        r[0] for r in con.execute("select distinct group_acronym from parliamentary_groups order by 1").fetchall()
    ]
    for g in [*groups, "NOPE"]:
        reqs += [
            f"partidos/{g}/deputados",
            f"partidos/{g}/voting-analytics",
            f"partidos/{g}/voting-analytics?legislatura=17",
        ]
        reqs += [f"partidos/{g}/voting-analytics?legislatura={leg}" for leg in legs]
    reqs += ["agenda/hoje", "agenda/semana"]
    return reqs


def _static_answers(out, requests):
    node = shutil.which("node")
    if node is None:
        if os.getenv("CI"):
            pytest.fail("node is required for the static contract in CI")
        pytest.skip("node is not installed")
    run = subprocess.run(
        [node, str(ANSWERS), str(out)], input=json.dumps(requests), capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_static_answers_equal_the_flask_answers(out, con, client, flask_app):
    requests = _requests(con, flask_app)
    answers = _static_answers(out, requests)
    checked = 0
    for endpoint, static in zip(requests, answers, strict=True):
        if not _on_duckdb(flask_app, endpoint):
            assert static["status"] in (404, 503), endpoint
            continue
        live = client.get(f"/api/{endpoint}")
        if live.status_code != 200:
            assert static["status"] == live.status_code, endpoint
            continue
        assert static["status"] == 200, endpoint
        assert static["body"] == live.get_json(), endpoint
        checked += 1
    assert checked >= 25


def test_agenda_says_not_available_until_s13(out):
    answers = _static_answers(out, ["agenda/hoje", "agenda/semana"])
    assert [a["status"] for a in answers] == [503, 503]
    assert [a["body"]["planned"] for a in answers] == ["S13", "S13"]


def test_attendance_is_in_each_deputy_file(out, con):
    from app.services import attendance

    bundle = json.loads((out / "deputados" / "1.json").read_text())
    assert bundle["attendance"] == json.loads(json.dumps(attendance.deputado_attendance(con, 1)))
    answers = _static_answers(out, ["deputados/1/attendance", "deputados/999999/attendance"])
    assert [a["status"] for a in answers] == [200, 404]
    assert answers[0]["body"]["legislaturas"][0]["reunioes"] == 6


# Worker count and DuckDB threads: a container reports the host's CPUs, not its own limit.


def test_export_workers_env_wins(tmp_path):
    (tmp_path / "cpu.max").write_text("400000 100000\n")
    assert export.default_workers({"EXPORT_WORKERS": "2"}, tmp_path / "cpu.max") == 2


@pytest.mark.parametrize(
    ("cpu_max", "expected"),
    [("200000 100000\n", 2), ("150000 100000\n", 2), ("50000 100000\n", 1)],
)
def test_export_workers_follow_the_cgroup_cpu_limit(tmp_path, cpu_max, expected):
    (tmp_path / "cpu.max").write_text(cpu_max)
    assert export.default_workers({}, tmp_path / "cpu.max") == expected


def test_export_workers_without_a_cgroup_limit(tmp_path):
    (tmp_path / "cpu.max").write_text("max 100000\n")
    assert export.default_workers({}, tmp_path / "cpu.max") == (os.cpu_count() or 1)
    assert export.default_workers({}, tmp_path / "missing") == (os.cpu_count() or 1)


def test_worker_connections_use_one_duckdb_thread(tmp_path, monkeypatch):
    db = tmp_path / "x.duckdb"
    duckdb.connect(str(db)).close()
    opened = []
    real = duckdb.connect

    class Kept:
        # The worker closes its connection; keep it open to read the setting afterwards.
        def __init__(self, con):
            self.con = con

        def __getattr__(self, name):
            return getattr(self.con, name)

        def close(self):
            pass

    def spy(*args, **kwargs):
        opened.append(Kept(real(*args, **kwargs)))
        return opened[-1]

    monkeypatch.setattr(export.duckdb, "connect", spy)
    export._deputy_chunk((str(db), str(tmp_path / "out"), []))
    assert [k.con.execute("select current_setting('threads')").fetchone()[0] for k in opened] == [1]


# Deputy files: a few queries per batch of people, not per person


SET_BASED = ("detalhes", "atividades", "voting-analytics")


class _Counting:
    """A connection that counts the queries run on it."""

    def __init__(self, con):
        self.con, self.queries = con, 0

    def execute(self, *args, **kwargs):
        self.queries += 1
        return self.con.execute(*args, **kwargs)


def _people(con):
    return [r[0] for r in con.execute("select distinct cadastro_id from deputy_legislatures order by 1").fetchall()]


def test_deputy_files_run_a_few_queries_per_batch_not_per_person(con, tmp_path, monkeypatch):
    people = _people(con)
    sections = tuple(s for s in export.DEPUTY_SECTIONS if s.endpoint in SET_BASED)
    assert len(sections) == len(SET_BASED)
    monkeypatch.setattr(export, "DEPUTY_SECTIONS", sections)
    monkeypatch.setattr(export, "CHUNK", len(people))
    counting = _Counting(con)
    files = export._render_deputies(counting, str(tmp_path), people)
    assert len(files) == len(people) > 400
    # One query per question for the whole batch, plus one per legislature for the few that
    # are asked per legislature. Per person it was over 20 queries each.
    assert counting.queries < 50


def test_a_deputy_file_is_the_same_in_any_batch(con, tmp_path, monkeypatch):
    people = _people(con)
    monkeypatch.setattr(export, "CHUNK", len(people))
    export._render_deputies(con, str(tmp_path / "one"), people)
    # One at a time, as a route reads them, for every tenth person.
    sample = people[::10]
    monkeypatch.setattr(export, "CHUNK", 1)
    export._render_deputies(con, str(tmp_path / "each"), sample)
    for cad in sample:
        path = f"deputados/{cad}.json"
        assert (tmp_path / "one" / path).read_bytes() == (tmp_path / "each" / path).read_bytes(), path
