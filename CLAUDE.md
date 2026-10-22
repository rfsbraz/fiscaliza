# Fiscaliza - Parliament Data Project

Portuguese Parliament open data analysis platform for government transparency.

---

## Project Overview

### Tech Stack
- **Data**: parlamento-aberto releases, loaded by `fiscaliza_data` into a local read-only DuckDB file
- **Backend**: Flask 3.0 over DuckDB (no ORM, no database server)
- **Frontend**: React 18 + Vite, same-origin `/api`

### Structure
```
├── app/                    # Flask API
│   ├── data/               # connection.py (read-only DuckDB, live swap), repository.py (all SQL), deputy_rows.py (deputy page rows for many people at once)
│   ├── services/           # the dicts each endpoint returns
│   └── routes/             # thin routes; pending.py answers 503 for data not released yet
├── fiscaliza_data/         # sync.py, seating.sql, views.sql
├── frontend/src/           # React components
└── tests/                  # pytest; tests/contracts pins what the frontend reads
```

---

## Critical Restrictions

### Do NOT Run
- **Deploy scripts**
- Anything that writes to GitHub releases or a production data directory

### Safe Operations
- Reading/editing code files
- Tests, `ruff`, `npm run build`
- The sync and the dev servers against a local `data/` folder

---

## Data Guidelines

- Data accuracy and integrity are paramount. Use only data that matches the source exactly.
- Never generate artificial data or provide defaults. If a mart is missing, the endpoint answers 503 with a reason.
- All SQL goes in `app/data/repository.py` or `fiscaliza_data/*.sql`. Services return plain dicts; routes stay 5 to 10 lines.
- Every endpoint the frontend calls has a contract in `tests/contracts/endpoints/`. Change the contract together with the component.
- Tests use synthetic fixture data only (`tests/site_data.py`), never real personal data.

---

## Workflow
- No commits without approval
- Request code review when ready
- Iterate based on feedback until approved
