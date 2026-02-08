# Fiscaliza - Parliament Data Project

Portuguese Parliament open data analysis platform for government transparency.

**Live**: https://fiscaliza.pt

---

## Project Overview

### Tech Stack
- **Backend**: Flask 3.0 + SQLAlchemy 2.0
- **Frontend**: React 18 + Vite
- **Database**: PostgreSQL (Aurora Serverless v2 in production)
- **Infrastructure**: AWS Lambda, Terraform, Docker

### Structure
```
├── app/                    # Flask API (blueprints, routes)
├── database/               # SQLAlchemy models (50+ tables)
├── scripts/                # Data import pipelines
├── frontend/src/           # React components
├── terraform/              # AWS infrastructure
└── ops/                    # Operational utilities
```

---

## Critical Restrictions

### Do NOT Run
- **Backend server** (`python main.py`, `flask run`, `gunicorn`)
- **Frontend server** (`npm run dev`, `npm start`)
- **Deploy scripts** (`deploy-*.sh`, `terraform apply`)
- **Docker compose** (`docker-compose up`)

The user is responsible for running servers and deployments.

### Safe Operations
- Reading/editing code files
- Running data import scripts
- Database migrations (`alembic upgrade`)
- Analysis and investigation scripts
- Tests

---

## Data Import Guidelines

### Core Principles
- Data accuracy and integrity are paramount
- Map XML to SQL directly unless instructed otherwise
- Document everything thoroughly
- Use only data that matches the source exactly
- Never generate artificial data or provide defaults

### Field Extraction Rules

**NEVER** use cascading `or` fallback patterns:

```python
# WRONG - Anti-pattern that obscures data provenance
dep_nome = (
    self._get_text_value(data_element, "DepNomeParlamentar")
    or self._get_text_value(data_element, "depNomeParlamentar")
    or self._get_text_value(data_element, "depNome")
)
```

**ALWAYS** use explicit field mapping:

```python
# CORRECT - Clear data provenance
dep_nome_parlamentar = self._get_text_value(data_element, "DepNomeParlamentar")
dep_nome_completo = self._get_text_value(data_element, "DepNomeCompleto")
```

**Why**:
- **Data Provenance**: Know exactly which XML field maps to which DB field
- **Debugging**: Trace bad data to exact XML source
- **Validation**: Verify expected XML structure is present
- **No Silent Failures**: XML structure changes cause explicit failures
- **Bug Prevention**: Prevent using same source value for different fields

### Import Process
1. Check for existing models before creating new ones (watch for naming variations)
2. Create related models and relations as needed
3. Import, process, and store every property
4. Design unified data model across all legislative periods (no versioned tables)
5. When marking fields as "mapped", rely on full XML hierarchy to prevent mixing fields from different contexts

### Import Pipeline States
```
discovered → downloading → pending → processing → completed
                                  ↘ failed / import_error / schema_mismatch
```

---

## Database Guidelines

### Key Models
- `Legislatura` - Parliamentary legislature/session
- `Deputado` - Parliamentary deputies
- `Partido` - Political parties
- `Coligacao` / `ColigacaoPartido` - Party coalitions
- `Commission` / `WorkGroup` / `SubCommittee` - Parliamentary organization
- `AgendaParlamentar` - Parliamentary agenda
- `ImportStatus` - Data import tracking

### Design Patterns
- UUID primary keys for distributed imports
- Timestamp tracking (created_at, updated_at)
- Foreign key constraints with proper relationships

---

## Field Management
- Don't derive fields from other fields without explicit data
- New fields allowed if well-justified and documented
- Document understanding of each field
- Update documentation when gaining new knowledge

---

## Schema Error Resolution
1. Check existing models (including poorly named ones)
2. Create/update related models if needed
3. Add necessary relations and fields
4. Ensure complete data import

---

## Workflow
- No commits without approval
- Request code review when ready
- Iterate based on feedback until approved
