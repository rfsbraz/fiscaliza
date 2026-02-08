# Fiscaliza

[![CI](https://github.com/rodrigobraz/fiscaliza/actions/workflows/ci.yml/badge.svg)](https://github.com/rodrigobraz/fiscaliza/actions/workflows/ci.yml)

Portuguese Parliament open data analysis platform for government transparency.

**Live at: [fiscaliza.pt](https://fiscaliza.pt)**

## Architecture

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask 3.0 + SQLAlchemy 2.0 |
| **Frontend** | React 18 + Vite |
| **Database** | PostgreSQL (Aurora Serverless v2 in production) |
| **Infrastructure** | AWS Lambda, Terraform, Docker |

```
├── app/                    # Flask API (blueprints, routes)
├── database/               # SQLAlchemy models (50+ tables)
├── scripts/                # Data import pipelines
├── frontend/src/           # React components
├── terraform/              # AWS infrastructure
└── ops/                    # Operational CLI utilities
```

## Quick Start

### Docker (recommended)

```bash
docker-compose up -d postgres    # Start PostgreSQL
docker-compose up backend        # Start Flask API
cd frontend && npm run dev       # Start React dev server
```

### Manual Setup

```bash
# Backend
pip install -r requirements.txt
FLASK_DEBUG=true python app/main.py

# Frontend
cd frontend
npm install
npm run dev
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development setup instructions.

## Data Pipeline

Fiscaliza imports and processes XML data from the [Portuguese Parliament Open Data portal](https://www.parlamento.pt/Cidadania/paginas/dadosabertos.aspx).

```bash
# Discover available files
python -m scripts.data_processing.pipeline_runner discover

# Import pending files
python -m scripts.data_processing.pipeline_runner import
```

### `ops` CLI

```bash
python -m ops.cli db status      # Database status
python -m ops.cli db migrate     # Run migrations
python -m ops.cli pipeline run   # Full pipeline run
```

## Database

PostgreSQL database with 50+ tables covering:

- Deputies and biographical information
- Political parties and parliamentary groups
- Legislative activities and voting records
- Parliamentary agenda and sessions
- Conflicts of interest declarations

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

[AGPL-3.0](LICENSE) - You are free to use, modify, and distribute this software. If you run a modified version on a network server, you must make the source code available to users.
