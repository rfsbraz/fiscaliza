# Fiscaliza

[![CI](https://github.com/rfsbraz/parliament/actions/workflows/ci.yml/badge.svg)](https://github.com/rfsbraz/parliament/actions/workflows/ci.yml)

Portuguese Parliament open data analysis platform for government transparency, at [fiscaliza.pt](https://fiscaliza.pt).

## Architecture

| Layer | Technology |
|-------|-----------|
| **Data** | [parlamento-aberto](https://github.com/rfsbraz/parlamento-aberto) releases, loaded into a local read-only DuckDB file |
| **Backend** | Flask 3.0 over DuckDB, served by gunicorn |
| **Frontend** | React 18 + Vite, calling `/api` on the same origin |

```
├── app/                    # Flask API: routes, services, data/repository.py (all SQL)
├── fiscaliza_data/         # Sync tool, seating rule and site views
├── frontend/src/           # React components
├── tests/                  # pytest, including the endpoint contracts
└── terraform/              # Old AWS infrastructure, kept until its destroy is confirmed
```

There is no database server. The sync builds `fiscaliza-<tag>.duckdb` from a release, checks it, and points `current.duckdb` at it. The API opens `$FISCALIZA_DATA_DIR/current.duckdb` read-only and picks up a new file within a minute, with no restart.

## Quick Start

```bash
pip install -r requirements.txt

# Build the data file from a local parlamento-aberto `release build` output
# (a folder, its manifest.json, or a .tar.gz/.tgz/.zip of the folder)
python -m fiscaliza_data.sync --from ../parlamento-aberto/dist --data-dir data

# API on :5000, then the frontend dev server, which proxies /api to it
FISCALIZA_DATA_DIR=data flask --app app.main run --port 5000
cd frontend && npm install && npm run dev
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full setup.

## Data sync

```bash
python -m fiscaliza_data.sync [--tag TAG] [--from PATH] [--data-dir DIR]
```

- With no `--from`, it reads the latest parlamento-aberto release on GitHub (or `--tag`), one unauthenticated API call.
- `--from PATH` reads a local `release build` output instead: the folder, its `manifest.json`, or a `.tar.gz`, `.tgz` or `.zip` of the folder. Use it before parlamento-aberto publishes releases. `--from-dir` still works as the old name.
- `--data-dir` defaults to `$FISCALIZA_DATA_DIR`, then `data`.
- `python -m fiscaliza_data sync` is the same command.

Every source goes through the same checks: SHA-256 of each Parquet file against the manifest, the schema major version, 230 seated deputies in the current legislature, and no table more than 5% smaller than the live one. A failure exits non-zero and leaves the previous file live. The last two files are kept.

## Not served yet

Attendance (`/api/deputados/<id>/attendance`) and the agenda for today and this week (`/api/agenda/hoje`, `/api/agenda/semana`) wait for their parlamento-aberto marts. They answer 503 with a reason, and the frontend shows its "indisponível" notice.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

[AGPL-3.0](LICENSE) - You are free to use, modify, and distribute this software. If you run a modified version on a network server, you must make the source code available to users.

The data comes from the Assembleia da República open data, reused under its terms, through parlamento-aberto (CC BY 4.0 for its derived tables). The site footer carries the attribution.
