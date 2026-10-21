"""The old Postgres and AWS stack is gone (S10).

The site reads only the DuckDB file the sync builds. Nothing may import the old database
package, the importers or the AWS tooling, and their packages are out of the requirements.
terraform/ stays until the `terraform destroy` is confirmed.
"""

import ast
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

REMOVED = [
    "database",
    "alembic.ini",
    "lambda-functions",
    "scripts",
    "ops",
    "ops.py",
    "examples",
    "app/database",
    "app/models",
    "app/utils",
    "app/routes/parlamento.py",
    "config",
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yml",
    "main.py",
    "run_tests.py",
    "analyze_deputy_issue.py",
    "investigate_data_quality.py",
    "investigate_deputy_count.py",
    "test_analytics_system.py",
    "test_comprehensive_mappers.py",
    "DEPLOYMENT_GUIDE.md",
    "SERVERLESS_MIGRATION.md",
    "IMPORT_STATUS_FLOW_SUMMARY.md",
    "POLITICAL_RESEARCH_GUIDE.md",
]
OLD_MODULES = {"database", "scripts", "ops", "config", "sqlalchemy", "flask_sqlalchemy", "alembic", "psycopg2", "boto3"}
OLD_PACKAGES = {
    "psycopg2",
    "psycopg2-binary",
    "boto3",
    "sqlalchemy",
    "flask-sqlalchemy",
    "alembic",
    "aiohttp",
    "aiofiles",
    "lxml",
    "beautifulsoup4",
}


def _tracked(*patterns):
    out = subprocess.run(["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / p for p in out.stdout.split()]


@pytest.mark.parametrize("path", REMOVED)
def test_old_stack_path_is_gone(path):
    assert not (ROOT / path).exists()


def test_no_bat_or_powershell_scripts_left():
    assert [p.name for p in _tracked("*.bat", "*.ps1")] == []


def test_terraform_stays_until_the_destroy_is_confirmed():
    assert (ROOT / "terraform" / "main.tf").is_file()


def test_no_python_file_imports_an_old_module():
    found = []
    for path in _tracked("*.py"):
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            found += [f"{path.relative_to(ROOT)}: {n}" for n in names if n.split(".")[0] in OLD_MODULES]
    assert found == []


def test_requirements_have_no_old_stack_packages():
    names = {
        re.split(r"[<>=!~\[ ;]", line.strip(), maxsplit=1)[0].lower()
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert names & OLD_PACKAGES == set()
    assert {"flask", "duckdb", "requests", "gunicorn"} <= names


def test_ci_has_no_postgres_service():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "postgres" not in ci.lower()
    assert "PG_" not in ci
