# Deployment guide

The project is prepared for a split deployment: Flask API + managed PostgreSQL, and a static React/Vite site. This workspace has no Git remote or hosting account connection, so no cloud services have been created and no live deployment has been performed.

## Environment configuration

Never put secrets in the repository. Set these values in the hosting provider's service settings:

| Variable | Backend | Frontend build | Meaning |
|---|---:|---:|---|
| `DATABASE_URL` | Yes | No | Provider's PostgreSQL connection URL. The backend normalizes common `postgres://` and `postgresql://` forms to psycopg 3. |
| `CORS_ORIGINS` | Yes | No | Comma-separated exact origins of the deployed frontend. |
| `VITE_API_BASE_URL` | No | Yes | Public API origin, without a trailing path. Vite embeds this at build time. |
| `VITE_MAP_TILE_URL` | No | Optional | Tile endpoint template; defaults to the OpenStreetMap standard raster endpoint. |
| `MAX_IMPORT_BYTES` | Yes | No | Upload limit in bytes (default 20 MiB). |
| `IMPORT_STORAGE_DIR` | Yes | No | Upload staging directory. Configure persistent storage if source files must survive service restarts. |

## Render setup

1. Push this repository to a Git host and create a managed PostgreSQL database and two services in the same region (Singapore is nearest the initial target cities among Render's documented regions).
2. For the API web service, set root directory to `backend`, build command to `pip install -r requirements.txt`, and start command to `gunicorn run:app --bind 0.0.0.0:$PORT`. Set `DATABASE_URL`, `CORS_ORIGINS`, and the import/log settings above.
3. Before serving traffic after the first database creation, run `flask db upgrade` from `backend/`, then run `python seed_cities.py` and `python seed_sources.py` once. For later releases, run migrations as a release/pre-deploy step supported by the selected service plan. Seed scripts are idempotent and can be rerun.
4. For the frontend static site, set root directory to `frontend`, build command to `npm ci && npm run build`, and publish directory to `dist`. Set `VITE_API_BASE_URL` to the API's public origin and rebuild whenever it changes.
5. Set backend `CORS_ORIGINS` to the exact frontend origin, then verify `/api/health`, city/source catalogs, an unavailable analytics response, and a manual CSV upload before accepting data.
6. Select paid/persistent database and service plans appropriate to retention, uptime, storage, and expected traffic. Render's free Postgres has a limited lifetime; it is unsuitable as the durable production database. Check current plan limits and pricing before provisioning.

## Operations and limitations

- The health endpoint checks PostgreSQL connectivity. Configure provider health checks to use `/api/health`.
- Uploaded files are written to `IMPORT_STORAGE_DIR`. A local container filesystem may be ephemeral; attach persistent storage or move raw files to an object store before relying on long-term source-file retention.
- No scheduled ingestion jobs are configured. Each provider connector has separate capability limits; add a worker/scheduler only after a source's API, terms, credentials, and refresh cadence are verified.
- OSM standard tiles are community-funded and best effort. Follow the tile usage policy, preserve visible attribution, honor caching, and choose an authorized tile provider or self-hosted service if production traffic requires service guarantees.
- Set `LOG_LEVEL` appropriately, monitor import failures/data-quality reports, and keep database backups and retention policies enabled.

## Local deployment checks

```sh
cd backend
flask db upgrade
python seed_cities.py
python seed_sources.py
gunicorn run:app --bind 0.0.0.0:5000
```

In another terminal:

```sh
cd frontend
npm ci
npm test
npm run build
```

Review current Render [Blueprint specifications](https://render.com/docs/blueprint-spec), [service types and plans](https://render.com/docs/service-types), and [PostgreSQL connection guidance](https://render.com/docs/postgresql-creating-connecting) before creating resources.
