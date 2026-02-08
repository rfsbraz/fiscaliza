# Contributing to Fiscaliza

Thank you for your interest in contributing to Fiscaliza! This project aims to bring transparency to Portuguese Parliament operations through open data analysis.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Docker)

### Option 1: Docker (recommended)

```bash
docker-compose up -d postgres    # Start PostgreSQL
docker-compose up backend        # Start Flask API (with hot reload)
cd frontend && npm run dev       # Start React dev server
```

### Option 2: Manual Setup

1. **Database**: Install PostgreSQL and create a database:
   ```bash
   createdb parliament
   ```

2. **Backend**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Frontend**:
   ```bash
   cd frontend
   npm install
   ```

4. **Environment**: Create `.env` with your database credentials:
   ```
   DATABASE_TYPE=postgresql
   PG_HOST=localhost
   PG_PORT=5432
   PG_USER=parluser
   PG_PASSWORD=parliament_dev
   PG_DATABASE=parliament
   ```

### Running the Import Pipeline

The data import pipeline downloads and processes XML data from the Portuguese Parliament open data portal:

```bash
# Discover available files
python -m scripts.data_processing.pipeline_runner discover

# Import all pending files
python -m scripts.data_processing.pipeline_runner import

# Retry failed imports
python -m scripts.data_processing.pipeline_runner import --retry-failed
```

The `ops` CLI provides additional management commands:

```bash
python -m ops.cli db status      # Check database status
python -m ops.cli db migrate     # Run pending migrations
python -m ops.cli pipeline run   # Run full import pipeline
```

## Running Tests

```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

## Code Style

### Python

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .          # Lint
ruff format .         # Format
```

### JavaScript/React

Follow existing patterns in the codebase. Key conventions:
- Functional components with hooks
- API calls through `apiFetch()` from `config/api.js`

### Pre-commit Hooks

Install pre-commit hooks to automatically check code before committing:

```bash
pip install pre-commit
pre-commit install
```

## Data Integrity

This project is entirely reliant on data accuracy. Key principles:

- **Never generate artificial data** or provide defaults where real data is missing
- **Map XML to SQL directly** unless instructed otherwise
- **Document everything** thoroughly
- **Fix importers, not data** - if data is wrong, fix the import pipeline

See `CLAUDE.md` for detailed data import guidelines.

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes following the code style guidelines
3. Ensure all tests pass
4. Submit a PR with a clear description of changes
5. Wait for code review

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.
