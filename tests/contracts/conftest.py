import pytest


@pytest.fixture
def contract_data_source():
    """The small fixture data source that ported service functions read.

    Nothing reads it yet. The PR that adds the DuckDB repository replaces this with a
    file built from tiny fixture Parquet, with no network and no database server.
    """
    return None
