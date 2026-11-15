# SmartCity IQ

An Indian urban intelligence platform built around traceable public data, explicit coverage, and clear provenance.

## Platform capabilities

The repository contains the Flask/SQLAlchemy API, provider connector framework, catalog/import/analytics APIs, raw and normalized ingestion paths, Alembic migrations, seed scripts, and a responsive React dashboard with domain views, source-aware tables, comparable-series charts, and a station coverage map. No measurement data is seeded. If no normalized observations or valid station coordinates are available, the UI explains that state instead of displaying invented values.

## Local setup

Requirements: Python 3.11+, Node.js 20+, and PostgreSQL 14+.

1. Create a PostgreSQL database named `smartcity_iq`.
2. Copy `.env.example` to `.env` and set `DATABASE_URL` for your local PostgreSQL instance.
3. Backend: `cd backend`, create/activate a virtual environment, install `pip install -r requirements.txt`, then run `flask db upgrade`, `python seed_cities.py`, and `python seed_sources.py`.
4. Start the API from `backend/` with `flask run`.
5. Frontend: in another terminal run `cd frontend`, optionally copy `.env.example` to `.env.local`, then run `npm install && npm run dev`. The Vite development proxy forwards `/api` to `http://127.0.0.1:5000` by default. Set `VITE_API_PROXY_TARGET` to override it or `VITE_API_BASE_URL` for a deployed API origin.

The health route is `GET /api/health`; it reports database connectivity and returns HTTP 503 if the database is unavailable. Catalog endpoints are listed in [API documentation](docs/api.md). CSV/Excel uploads are staged in raw form and are not included in analytics until explicitly processed. Run frontend checks with `cd frontend && npm test && npm run build`; backend checks with `cd backend && pip install -r requirements-dev.txt && pytest`.

## Documentation

- [Architecture and database notes](docs/database.md)
- [API foundation](docs/api.md)
- [Data source verification and coverage notes](docs/data-sources.md)
- [Processing and analytics](docs/processing.md)
- [Frontend foundation](docs/frontend.md)
- [Deployment preparation](docs/deployment.md)

Do not put credentials in source files. No measurement data is seeded by this project foundation.
