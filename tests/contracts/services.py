"""Which contracts have a service function behind them.

Maps a contract name (the file name in ``endpoints/`` without ``.json``) to a callable
that takes the test data source and returns the endpoint's JSON payload as a dict.

Nothing is ported to the new data layer yet, so the map is empty and every contract
test is an expected failure. Each PR that ports an endpoint adds its entry here, and
its contract test then has to pass.
"""

PORTED = {}
