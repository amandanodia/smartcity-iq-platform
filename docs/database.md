# Database foundation

The schema uses a shared registry (`data_sources`, `datasets`, `dataset_coverage`) and explicit provenance on domain observations. `cities` and hierarchical `geographic_areas` are data records, allowing new cities without code changes. Domain observations preserve original and normalized values/units separately and point back to a dataset/source reference.

Tables include: cities, data_sources, datasets, dataset_coverage, air_quality, monitoring_stations, traffic_statistics, road_accidents, water_statistics, population_statistics, infrastructure, geographic_areas, dataset_files, import_batches, data_refresh_logs, and data_quality_reports.

Coordinates have range constraints. Observation tables have date/geography indexes. PostgreSQL JSONB stores provider-specific metadata without pretending source schemas are identical. Geometry is represented as optional GeoJSON JSONB in this initial migration; PostGIS conversion is deferred until spatial query requirements are implemented.

Apply schema changes with `flask db upgrade` from `backend/`. Seed the eight initial cities with `python seed_cities.py`. The seed command is idempotent by city slug.
