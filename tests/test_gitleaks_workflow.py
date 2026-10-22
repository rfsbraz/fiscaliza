"""The gitleaks workflow scans the full history of master, with a rule for *_PASSWORD= lines.

The default gitleaks rules have no rule for a plain env-file line such as a database password
assignment, which is how a production password once reached a branch of this repo.
"""

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "gitleaks.yml"
CONFIG = ROOT / ".gitleaks.toml"

# Built at runtime, so this file holds no line the rule itself would flag.
NAME = "PG" + "_PASSWORD"


def _config():
    return tomllib.loads(CONFIG.read_text())


def _rule():
    (rule,) = [r for r in _config()["rules"] if r["id"] == "password-assignment"]
    return rule


def _secret(line):
    """What the rule reports for one line, or None, after the rule's own allowlist."""
    rule = _rule()
    match = re.search(rule["regex"], line + "\n")
    if not match:
        return None
    secret = match.group(rule["secretGroup"])
    for allow in rule.get("allowlists", []):
        if any(re.search(r, secret) for r in allow.get("regexes", [])):
            return None
    return secret


def test_workflow_scans_the_full_history_of_master():
    t = WORKFLOW.read_text()
    assert re.search(r"push:\s*\n\s*branches: \[master\]", t)
    assert re.search(r"pull_request:\s*\n\s*branches: \[master\]", t)
    assert "schedule:" in t
    assert "fetch-depth: 0" in t
    (scan,) = re.findall(r"run: (gitleaks git .*)", t)
    assert '--log-opts="--full-history HEAD"' in scan
    # --all would pull in other branches and the closed Dependabot PR refs.
    assert "--all" not in scan
    assert "--redact" in scan
    assert "--exit-code 1" in scan
    assert "--config .gitleaks.toml" in scan


def test_workflow_pins_and_verifies_the_gitleaks_download():
    t = WORKFLOW.read_text()
    assert re.search(r"GITLEAKS_VERSION: \d+\.\d+\.\d+", t)
    assert re.search(r"GITLEAKS_SHA256: [0-9a-f]{64}", t)
    assert "sha256sum -c" in t


def test_workflow_token_is_read_only():
    t = WORKFLOW.read_text()
    assert re.search(r"permissions:\s*\n\s*contents: read", t)
    assert "persist-credentials: false" in t


def test_config_extends_the_default_rules():
    assert _config()["extend"]["useDefault"] is True


@pytest.mark.parametrize(
    "line",
    [
        f"{NAME}=Tr0ub4dor-and-3",
        f"export {NAME}=Tr0ub4dor-and-3",
        f'{NAME}="Tr0ub4dor-and-3"',
        f"{NAME} = 'Tr0ub4dor-and-3'",
        f"  - DB_{NAME}=Tr0ub4dor-and-3",
        f"{NAME}=Tr0ub4dor-and-3  # prod",
        # Shell-special characters are still a literal value, not a variable reference.
        f"{NAME}=$Xr(3)<x>=?]!_9",
        f"POSTGRES{NAME[2:]}=Tr0ub4dor-and-3",
    ],
)
def test_rule_flags_a_literal_password(line):
    assert _secret(line)


@pytest.mark.parametrize(
    "line",
    [
        f"{NAME}=",
        f"{NAME}=$" + NAME,
        f"{NAME}=${{{NAME}}}",
        f'{NAME}="${{{NAME}}}"',
        f'{NAME} = os.environ.get("{NAME}")',
        f"{NAME}=${{{{ secrets.{NAME} }}}}",
        f"password={NAME}",
        f"# set {NAME}=... in your .env",
    ],
)
def test_rule_skips_references_and_empty_values(line):
    assert _secret(line) is None
