# Frontend foundation

The React app uses React Router for the module pages, Tailwind CSS for responsive layout, Lucide React for icons, and one shared city/date filter context. Data access is centralized in `frontend/src/services/api.ts`.

Available pages include Overview, City Comparison, Traffic & Mobility, Air Quality, Road Safety, Water & Resources, Urban Development (population and infrastructure), Data Sources, Data Quality, and About Project. Analytics tables render API results with source, record class, units, observation counts, reporting periods, and geographic coverage. Missing data is shown as an explicit empty state; the UI does not insert demo values.

The dashboard only shows record counts returned by the backend. It labels capped result counts as lower bounds and states that freshness cannot be determined until refresh timestamps are exposed by the API. Interactive Chart.js charts require a comparable series filter; the Leaflet map uses only stored, validated station coordinates and source links.

During local development Vite proxies `/api` to `http://127.0.0.1:5000`. Set `VITE_API_PROXY_TARGET` to use another backend URL. Production builds can set `VITE_API_BASE_URL` to the backend origin. Copy `frontend/.env.example` to `.env.local` for local overrides.

The OpenStreetMap standard raster tile endpoint is configurable with `VITE_MAP_TILE_URL`. The default uses the policy endpoint and visible attribution; the public tile service is best effort and should be replaced with a contracted provider or self-hosted tiles if usage grows.
