"""The community files a public repo needs, in pt-PT, and no agent-specific CLAUDE.md."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FORMS = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))


@pytest.mark.parametrize(
    "path, heading",
    [
        ("SECURITY.md", "# Segurança"),
        ("CODE_OF_CONDUCT.md", "# Pacto de Código de Conduta"),
        ("AGENTS.md", "# Instruções para agentes"),
        ("CONTRIBUTING.md", "# Como contribuir"),
    ],
)
def test_community_file_is_there_in_pt_pt(path, heading):
    assert (ROOT / path).read_text().startswith(heading)


def test_claude_md_is_replaced_by_agents_md():
    assert not (ROOT / "CLAUDE.md").exists()


def test_security_points_to_private_reporting():
    assert "https://github.com/rfsbraz/parliament/security/advisories/new" in (ROOT / "SECURITY.md").read_text()


def test_pull_request_template_sections():
    t = (ROOT / ".github" / "pull_request_template.md").read_text()
    for heading in ["## O quê e porquê?", "## Como foi testado?", "## Capturas de ecrã", "## Uso de IA"]:
        assert heading in t
    assert "Closes #" in t


def test_issue_forms_are_in_pt_pt():
    # No YAML parser in the requirements, so this reads the top-level keys as text.
    names = {}
    for form in FORMS:
        t = form.read_text()
        if form.name == "config.yml":
            assert re.findall(r"url: (\S+)", t)
            assert all(u.startswith("https://github.com/rfsbraz/") for u in re.findall(r"url: (\S+)", t))
            continue
        assert re.search(r"^body:\n", t, re.M), form.name
        assert set(re.findall(r"- type: (\w+)", t)) <= {"markdown", "input", "textarea", "dropdown", "checkboxes"}
        names[form.name] = re.search(r"^name: (.+)$", t, re.M).group(1)
    assert names == {"erro-no-site.yml": "Erro no site", "numero-errado.yml": "Número errado no site"}


def test_wrong_number_form_points_to_the_source_data_form():
    t = (ROOT / ".github" / "ISSUE_TEMPLATE" / "numero-errado.yml").read_text()
    assert "parlamento-aberto/issues/new?template=correcao-de-dados.yml" in t


BRAND_LINE = (
    "O nome Fiscaliza e o logótipo não estão abrangidos pela AGPL. "
    "Quem publicar um fork tem de usar outro nome e outro logótipo."
)


def test_readme_says_the_name_and_logo_are_not_under_the_agpl():
    licence = (ROOT / "README.md").read_text().split("## Licença", 1)[1].split("\n## ", 1)[0]
    assert BRAND_LINE in licence
