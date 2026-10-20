"""Unit tests for the contract checker itself."""

from tests.contracts.checker import check

CONTRACT = {
    "keys": [
        {"path": "nome", "type": "string", "nullable": False},
        {"path": "idade", "type": "number", "nullable": True},
        {"path": "ativo", "type": "boolean", "nullable": False},
        {"path": "partido", "type": "object", "nullable": True},
        {"path": "partido.sigla", "type": "scalar", "nullable": False},
        {"path": "mandatos", "type": "array", "nullable": False},
        {"path": "mandatos[].legislatura", "type": "scalar", "nullable": False},
        {"path": "mandatos[].votos", "type": "mapping", "nullable": True},
    ]
}

GOOD = {
    "nome": "Ana",
    "idade": 40,
    "ativo": True,
    "partido": {"sigla": "PS"},
    "mandatos": [{"legislatura": "XVII", "votos": {"favor": 3}}, {"legislatura": "XVI"}],
}


def test_good_payload_passes():
    assert check(GOOD, CONTRACT) == []


def test_missing_required_key_fails():
    payload = {**GOOD}
    del payload["nome"]
    assert check(payload, CONTRACT) == ["nome: missing"]


def test_null_required_key_fails():
    assert check({**GOOD, "ativo": None}, CONTRACT) == ["ativo: null but not nullable"]


def test_nullable_key_may_be_missing_or_null():
    payload = {**GOOD, "idade": None}
    del payload["partido"]
    assert check(payload, CONTRACT) == []


def test_children_of_a_missing_nullable_parent_are_skipped():
    assert check({**GOOD, "partido": None}, CONTRACT) == []


def test_wrong_type_fails():
    assert check({**GOOD, "idade": "40"}, CONTRACT) == ["idade: expected number, got str"]


def test_bool_is_not_a_number():
    assert check({**GOOD, "idade": True}, CONTRACT) == ["idade: expected number, got bool"]


def test_every_array_element_is_checked():
    payload = {**GOOD, "mandatos": [{"legislatura": "XVII"}, {"legislatura": ["XVI"]}]}
    assert check(payload, CONTRACT) == ["mandatos[1].legislatura: expected scalar, got list"]


def test_empty_array_passes():
    assert check({**GOOD, "mandatos": []}, CONTRACT) == []


def test_mapping_must_be_an_object():
    payload = {**GOOD, "mandatos": [{"legislatura": "XVII", "votos": [1, 2]}]}
    assert check(payload, CONTRACT) == ["mandatos[0].votos: expected mapping, got list"]


def test_top_level_must_be_an_object():
    assert check([], CONTRACT) == ["<root>: expected object, got list"]
