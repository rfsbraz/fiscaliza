import duckdb
import pytest

from tests.site_data import build_site_data


@pytest.fixture(scope="session")
def site_data_dir(tmp_path_factory):
    """The synthetic release from tests/site_data.py, synced into the site's DuckDB file."""
    return build_site_data(tmp_path_factory.mktemp("site"))


@pytest.fixture
def contract_data_source(site_data_dir):
    """A read-only connection to that file, as the app opens it. No network, no server."""
    con = duckdb.connect(str(site_data_dir / "current.duckdb"), read_only=True)
    yield con
    con.close()
