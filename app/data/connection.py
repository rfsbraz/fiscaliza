"""Open the live DuckDB file read-only and hand out one cursor per request.

fiscaliza_data sync points ``current.duckdb`` at a new file when a release goes live. Each
process keeps one read-only connection and checks the link at most once a minute; when it
points at another file, the next request opens that one. No restart, no downtime.
"""

import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import duckdb

CURRENT = "current.duckdb"
CHECK_EVERY = 60
EXTENSION = "fiscaliza_data"


class DataUnavailable(Exception):
    """There is no live data file yet, or it cannot be opened."""


class DataSource:
    def __init__(self, data_dir, check_every=CHECK_EVERY, clock=time.monotonic):
        self.current = Path(data_dir) / CURRENT
        self.check_every = check_every
        self.clock = clock
        self._lock = threading.Lock()
        self._con = None
        self._target = None
        self._checked = None
        # The connection before the last swap stays referenced, so cursors still open on it
        # keep working until their request ends.
        self._previous = None

    def _connection(self):
        with self._lock:
            now = self.clock()
            if self._con is not None and now - self._checked < self.check_every:
                return self._con
            self._checked = now
            target = os.path.realpath(self.current)
            if self._con is not None and target == self._target:
                return self._con
            if not os.path.isfile(target):
                if self._con is not None:
                    return self._con
                raise DataUnavailable(f"no data file at {self.current}")
            try:
                con = duckdb.connect(target, read_only=True)
            except duckdb.Error as e:
                if self._con is not None:
                    return self._con
                raise DataUnavailable(f"cannot open {target}: {e}") from None
            self._previous, self._con, self._target = self._con, con, target
            return con

    @contextmanager
    def cursor(self):
        cur = self._connection().cursor()
        try:
            yield cur
        finally:
            cur.close()


def init_app(app, data_dir=None):
    """Attach a DataSource to the Flask app. The folder comes from the argument, then the
    FISCALIZA_DATA_DIR setting or environment variable, then ./data."""
    folder = data_dir or app.config.get("FISCALIZA_DATA_DIR") or os.getenv("FISCALIZA_DATA_DIR") or "data"
    app.extensions[EXTENSION] = DataSource(folder)
    return app.extensions[EXTENSION]


def data_source(app):
    source = app.extensions.get(EXTENSION)
    return source if source is not None else init_app(app)
