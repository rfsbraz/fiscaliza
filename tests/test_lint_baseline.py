"""The ruff baseline in pyproject.toml must only cover the legacy files.

The legacy code has thousands of ruff violations and isn't formatted, and the
migration to parlamento-aberto rewrites or deletes it. Until then pyproject.toml
lists, per legacy file, the rule codes it already breaks, and excludes the
unformatted legacy files from ``ruff format``. These tests check that the
baseline keeps the repo green without letting new code through.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"

# A legacy file that is in the baseline for both lint and format.
LEGACY_FILE = "analyze_deputy_issue.py"

# New modules, one in a new package and one beside legacy code.
NEW_FILES = ["fiscaliza_data/new_module.py", "app/routes/new_module.py"]

LINT_VIOLATION = "import os\n"  # F401, unused import
FORMAT_VIOLATION = "x = {  'a':1 }\n"


def _ruff_cmd():
    if shutil.which("ruff"):
        return ["ruff"]
    try:
        import ruff  # noqa: F401
    except ImportError:
        pytest.skip("ruff is not installed")
    return [sys.executable, "-m", "ruff"]


def ruff(*args, stdin=None):
    return subprocess.run(
        [*_ruff_cmd(), *args],
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_repo_passes_ruff_check():
    result = ruff("check", ".")
    assert result.returncode == 0, result.stdout[-2000:]


def test_repo_passes_ruff_format_check():
    result = ruff("format", "--check", ".")
    assert result.returncode == 0, result.stdout[-2000:]


def test_legacy_file_passes_when_named_directly():
    assert ruff("check", LEGACY_FILE).returncode == 0
    assert ruff("format", "--check", LEGACY_FILE).returncode == 0


@pytest.mark.parametrize("filename", NEW_FILES)
def test_new_file_with_lint_violation_fails(filename):
    result = ruff("check", "--stdin-filename", filename, "-", stdin=LINT_VIOLATION)
    assert result.returncode == 1
    assert "F401" in result.stdout


@pytest.mark.parametrize("filename", NEW_FILES)
def test_new_file_with_format_violation_fails(filename):
    result = ruff("format", "--check", "--stdin-filename", filename, "-", stdin=FORMAT_VIOLATION)
    assert result.returncode == 1


def test_ruff_is_pinned_to_one_version_in_ci():
    # The baseline was generated with this version; a new release can add rules or change formatting.
    pins = set(re.findall(r"ruff==([0-9.]+)", CI.read_text()))
    assert len(pins) == 1, f"expected one pinned ruff version in ci.yml, found {pins or 'none'}"
