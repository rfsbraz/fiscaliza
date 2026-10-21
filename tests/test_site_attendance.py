"""S11: plenary attendance (F12) on the DuckDB data layer.

Figures are worked out by hand from the lists in tests/site_data.py (ATTENDANCE). The rate is
present, in another body or on mission, over the ordinary and extraordinary sittings in the
lists; solemn and commemorative sittings are counted apart. The strict rate is present only.
"""

import shutil
from pathlib import Path

import duckdb
import pytest

from app.services import activity, attendance, core, deputies
from tests.site_data import build_site_data

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "frontend" / "src" / "components" / "DeputadoDetalhes.jsx"
PANEL = ROOT / "frontend" / "src" / "components" / "deputy" / "AttendancePanel.jsx"


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture
def con(data_dir):
    c = duckdb.connect(str(data_dir / "current.duckdb"), read_only=True)
    yield c
    c.close()


def _leg(payload, name):
    (found,) = [leg for leg in payload["legislaturas"] if leg["legislatura"] == name]
    return found


def _counts(**kwargs):
    base = {
        "presente": 0,
        "outro_orgao_ou_missao": 0,
        "justificadas": 0,
        "quorum_votacao": 0,
        "por_justificar": 0,
        "nao_classificadas": 0,
        "injustificadas": 0,
    }
    base.update(kwargs)
    return base


def test_person_1_in_xvii_by_hand(con):
    # 9000 PR, 9001 PR, 9002 ME, 9003 FJ, 9005 FA (33 days old: pending), 9006 PR.
    # 9004 is solemn (FI there) and stays out of the rate.
    leg = _leg(attendance.deputado_attendance(con, 1), "XVII")
    assert leg["com_listas"] is True
    assert leg["grupos"] == ["PSD"]
    assert leg["reunioes"] == 6
    assert leg["contagens"] == _counts(presente=3, outro_orgao_ou_missao=1, justificadas=1, por_justificar=1)
    assert leg["taxa_presenca"] == round(4 / 6 * 100, 1)
    assert leg["taxa_presenca_estrita"] == 50.0
    assert leg["solenes"] == {"reunioes": 1, "contagens": _counts(injustificadas=1)}
    assert (leg["primeira_reuniao"], leg["ultima_reuniao"]) == ("2025-10-16", "2026-10-15")
    assert leg["em_curso"] is True


def test_person_2_unclassified_quorum_and_other_body(con):
    # 9001 FA (278 days old: unclassified), 9002 QV, 9003 PNO, 9006 FI, the rest PR.
    leg = _leg(attendance.deputado_attendance(con, 2), "XVII")
    assert leg["reunioes"] == 6
    assert leg["contagens"] == _counts(
        presente=2, outro_orgao_ou_missao=1, quorum_votacao=1, nao_classificadas=1, injustificadas=1
    )
    assert leg["taxa_presenca"] == 50.0
    assert leg["taxa_presenca_estrita"] == round(2 / 6 * 100, 1)


def test_legislature_figure_pools_every_seat_on_the_lists(con):
    # XVII: 6 sittings x 230 seats = 1380 rows. Not counted as attended: FJ and FA (person 1),
    # FA, QV and FI (person 2). Strict also leaves out ME and PNO.
    leg = _leg(attendance.deputado_attendance(con, 1), "XVII")
    assert leg["legislatura_taxa_presenca"] == round(1375 / 1380 * 100, 1)
    assert leg["legislatura_taxa_presenca_estrita"] == round(1373 / 1380 * 100, 1)
    # XVI: 3 x 230 = 690. FIJ (person 1) and QVJ (301) are justified; CO and MP are elsewhere.
    leg = _leg(attendance.deputado_attendance(con, 1), "XVI")
    assert leg["legislatura_taxa_presenca"] == round(688 / 690 * 100, 1)
    assert leg["legislatura_taxa_presenca_estrita"] == round(686 / 690 * 100, 1)


def test_old_codes_pt_co_fij_by_hand(con):
    leg = _leg(attendance.deputado_attendance(con, 1), "XVI")
    assert leg["grupos"] == ["PS"]
    assert leg["reunioes"] == 3
    assert leg["contagens"] == _counts(presente=1, outro_orgao_ou_missao=1, justificadas=1)
    assert leg["taxa_presenca"] == round(2 / 3 * 100, 1)
    assert leg["taxa_presenca_estrita"] == round(1 / 3 * 100, 1)
    assert leg["em_curso"] is False
    assert [(r["data"], r["codigo"], r["categoria"]) for r in leg["registos"]] == [
        ("2025-03-13", "FIJ", "justified"),
        ("2024-10-10", "CO", "other_body_or_mission"),
    ]


def test_records_list_every_sitting_that_was_not_a_plain_presence_newest_first(con):
    leg = _leg(attendance.deputado_attendance(con, 1), "XVII")
    assert leg["registos"] == [
        {
            "data": "2026-09-17",
            "reuniao_id": 9005,
            "tipo_reuniao": "Ordinária",
            "solene": False,
            "codigo": "FA",
            "categoria": "pending",
            "descricao": "Falta ainda sem classificação",
            "grupo": "PSD",
        },
        {
            "data": "2026-04-25",
            "reuniao_id": 9004,
            "tipo_reuniao": "Solene",
            "solene": True,
            "codigo": "FI",
            "categoria": "unjustified",
            "descricao": "Falta injustificada",
            "grupo": "PSD",
        },
        {
            "data": "2026-03-12",
            "reuniao_id": 9003,
            "tipo_reuniao": "Extraordinária",
            "solene": False,
            "codigo": "FJ",
            "categoria": "justified",
            "descricao": "Falta justificada",
            "grupo": "PSD",
        },
        {
            "data": "2026-02-12",
            "reuniao_id": 9002,
            "tipo_reuniao": "Ordinária",
            "solene": False,
            "codigo": "ME",
            "categoria": "other_body_or_mission",
            "descricao": "Ausência em missão parlamentar",
            "grupo": "PSD",
        },
    ]


def test_never_the_absence_reason(con):
    payload = attendance.deputado_attendance(con, 1)
    keys = {k for leg in payload["legislaturas"] for r in leg["registos"] for k in r}
    keys |= {k for leg in payload["legislaturas"] for k in leg}
    for word in ("motivo", "reason", "justification", "observations", "justificacao"):
        assert not [k for k in keys if word in k.lower()]


def test_legislatures_newest_first_and_definition_stated(con):
    payload = attendance.deputado_attendance(con, 1)
    assert payload["id_cadastro"] == 1
    assert [leg["legislatura"] for leg in payload["legislaturas"]] == ["XVII", "XVI"]
    assert payload["definicao"]["taxa_presenca"]
    assert payload["definicao"]["taxa_presenca_estrita"]
    codes = {c["codigo"]: c for c in payload["codigos"]}
    assert codes["PT"]["categoria"] == "present"
    assert codes["CO"]["categoria"] == "other_body_or_mission"
    assert codes["FA"]["categoria"] == "pending"
    assert payload["atualizado"] == "2026-10-20"


def test_substitutes_have_only_their_own_sittings(con):
    # 231 sat until 2025-12-31 (only 9000); 232 from 2026-01-01 (9001 to 9006, 9004 solemn).
    leg = _leg(attendance.deputado_attendance(con, 231), "XVII")
    assert (leg["reunioes"], leg["taxa_presenca"], leg["solenes"]["reunioes"]) == (1, 100.0, 0)
    leg = _leg(attendance.deputado_attendance(con, 232), "XVII")
    assert (leg["reunioes"], leg["taxa_presenca"], leg["solenes"]["reunioes"]) == (5, 100.0, 1)
    assert leg["registos"] == []


def test_unknown_or_never_seated_person_is_not_found(con):
    for cad in (99999, 500):
        with pytest.raises(core.NotFound):
            attendance.deputado_attendance(con, cad)


def test_a_legislature_without_lists_says_so_instead_of_zeros(data_dir, tmp_path):
    copy = tmp_path / "copy.duckdb"
    shutil.copy(data_dir / "current.duckdb", copy)
    c = duckdb.connect(str(copy))
    try:
        c.execute("delete from plenary_attendance where legislature = 'XVI'")
        leg = _leg(attendance.deputado_attendance(c, 1), "XVI")
        assert leg["com_listas"] is False
        for key in ("reunioes", "contagens", "taxa_presenca", "taxa_presenca_estrita", "solenes"):
            assert leg[key] is None, key
        assert leg["registos"] == []
        assert leg["legislatura_taxa_presenca"] is None
        # The profile card uses the latest legislature that has lists.
        assert deputies.detalhes(c, 300)["estatisticas"]["assiduidade"] is None
    finally:
        c.close()


# Profile card and agenda stats


def test_profile_card_uses_the_latest_legislature_with_lists(con):
    assert deputies.detalhes(con, 1)["estatisticas"]["assiduidade"] == {
        "legislatura": "XVII",
        "reunioes": 6,
        "taxa_presenca": round(4 / 6 * 100, 1),
        "taxa_presenca_estrita": 50.0,
    }
    assert deputies.detalhes(con, 300)["estatisticas"]["assiduidade"] == {
        "legislatura": "XVI",
        "reunioes": 3,
        "taxa_presenca": 100.0,
        "taxa_presenca_estrita": 100.0,
    }


def test_no_default_or_capped_rate(con):
    s = deputies.detalhes(con, 232)["estatisticas"]
    assert s["assiduidade"]["taxa_presenca"] == 100.0
    assert "taxa_assiduidade" not in s


def test_agenda_stats_average_attendance_for_the_year(con):
    # 2026 up to the reference day: 9001, 9002, 9003, 9005, 9006 (9004 is solemn), 5 x 230 = 1150
    # seats; 5 not attended (person 1: FJ, FA; person 2: FA, QV, FI).
    stats = activity.estatisticas_atividade(con)["estatisticas"]
    assert stats["assiduidade"] == {"media_presencas": round(1145 / 1150 * 100, 1), "reunioes": 5}


# Routes


@pytest.fixture
def site_app(app, data_dir):
    from app.data import connection

    before = app.extensions.get(connection.EXTENSION)
    connection.init_app(app, data_dir)
    yield app
    app.extensions[connection.EXTENSION] = before


def test_route_serves_the_service_payload(site_app, con):
    client = site_app.test_client()
    response = client.get("/api/deputados/1/attendance")
    assert response.status_code == 200
    assert response.get_json() == attendance.deputado_attendance(con, 1)
    assert client.get("/api/deputados/99999/attendance").status_code == 404


def test_route_is_on_the_deputies_blueprint_not_the_old_code(app):
    endpoints = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert endpoints["/api/deputados/<int:cad_id>/attendance"].startswith("deputies.")
    assert "meeting_attendances" not in (ROOT / "app" / "routes" / "parlamento.py").read_text()


# Deputy page


def test_attendance_tab_is_on_and_reads_the_panel():
    source = COMPONENT.read_text()
    assert "ATTENDANCE_AVAILABLE" not in source
    assert "apiFetch(`deputados/${cadId}/attendance`)" in source
    assert "{ id: 'attendance', label: 'Presenças', icon: Activity }" in source
    assert "<AttendancePanel" in source


def test_no_made_up_average_or_threshold_left():
    source = COMPONENT.read_text() + PANEL.read_text()
    assert "87.5" not in source
    assert "parliamentAverage" not in source
    assert "considera uma taxa acima" not in source
    assert "Motivo:" not in source
