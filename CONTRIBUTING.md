# Contributing to Fiscaliza

Thank you for your interest in contributing to Fiscaliza! This project aims to bring transparency to Portuguese Parliament operations through open data analysis.

## Development Setup

### Prerequisites

- Python 3.12
- Node.js 20+
- A parlamento-aberto `release build` output, or network access to its GitHub releases

No database server is needed.

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff==0.17.1
```

### Data

The API serves one read-only DuckDB file. Build it with the sync:

```bash
# From a local parlamento-aberto build: the folder, its manifest.json, or an archive of it
python -m fiscaliza_data.sync --from ../parlamento-aberto/dist --data-dir data

# Or from a published release
python -m fiscaliza_data.sync --tag data-2026-10-20 --data-dir data
```

The command exits non-zero when a check fails and leaves the previous file live. Run it again with a newer build to swap the file in; the running API picks it up within a minute.

### Running locally

```bash
FISCALIZA_DATA_DIR=data flask --app app.main run --port 5000
cd frontend && npm install && npm run dev   # proxies /api to :5000
```

## Running Tests

```bash
pytest                 # everything, including tests/contracts
pytest tests/contracts # the endpoint contracts only
cd frontend && npm run build
```

The tests build tiny synthetic releases. They need no network and no real data.

## Code Style

### Python

We use [ruff](https://docs.astral.sh/ruff/) 0.17.1 for linting and formatting:

```bash
ruff check .          # Lint
ruff format .         # Format
```

All SQL lives in `app/data/repository.py` and `fiscaliza_data/*.sql`. Routes parse arguments, call a service in `app/services/`, and return its dict as JSON.

### JavaScript/React

Follow existing patterns in the codebase. Key conventions:
- Functional components with hooks
- API calls through `apiFetch()` from `config/api.js`

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Data Integrity

This project is entirely reliant on data accuracy. Key principles:

- **Never generate artificial data** or provide defaults where real data is missing.
- If a figure is wrong, fix it where it is computed: in parlamento-aberto for the marts, or in this repo's views and services. Never patch the data file.
- When a mart does not exist yet, the endpoint says so (503 with a reason) and the page shows a notice. No placeholder numbers.

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes following the code style guidelines
3. Ensure all tests pass
4. Submit a PR with a clear description of changes
5. Wait for code review

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.
