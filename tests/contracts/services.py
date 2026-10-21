"""Which contracts have a service function behind them.

Maps a contract name (the file name in ``endpoints/`` without ``.json``) to a callable
that takes the test data source (a read-only DuckDB connection to the synthetic release in
``tests/site_data.py``) and returns the endpoint's JSON payload as a dict, called with the
arguments the frontend sends.

Each PR that ports an endpoint adds its entry here, and its contract test then has to pass.
Endpoints not listed are expected failures until they are ported.
"""

from app.services import activity, core

PORTED = {
    "legislaturas": core.legislaturas,
    "estatisticas": core.estatisticas,
    "deputados": lambda con: core.deputados(con, page=1, per_page=20, active_only=False),
    "partidos": core.partidos,
    "coligacoes": lambda con: core.coligacoes(con, include_inactive=True),
    "coligacao": lambda con: core.coligacao(con, "AD"),
    "coligacao_deputados": lambda con: core.coligacao_deputados(con, "AD"),
    "coligacao_partidos": lambda con: core.coligacao_partidos(con, "AD"),
    "votacoes_recentes": lambda con: activity.votacoes_recentes(con, limite=5),
    "estatisticas_atividade": activity.estatisticas_atividade,
}
