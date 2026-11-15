# Processing and analytics

`POST /api/import-batches/{id}/process` requires an explicit source-header mapping. The pipeline does not infer provider schemas. It trims and exactly matches city labels to the configured city records (optional aliases must be supplied), parses numeric values and dates with Pandas, requires an explicit IANA timezone for naive timestamps, converts timestamps to UTC, applies only an explicitly supplied unit conversion, detects duplicate rows, and records rejected-row reasons in the import summary and data-quality report.

Original files and source-shaped raw rows remain stored. Accepted domain observations retain original and normalized values/units, source URL, import batch, and the complete source row in provenance metadata. Missing or invalid values remain in raw staging and are excluded from normalized storage; they are never replaced with zero. Population rows require a reference year. Air-quality rows require an observation date. Annual traffic, road-safety, and water records may use a reference year, stored as period end only when the source row has no more precise observation date.

Analytics summarize only non-null normalized values. They group by dataset, city/area, category, and normalized unit, and return mean, minimum, maximum, observation count, reporting period, coverage, record class, and source. Results for different datasets or units are kept separate. No measures are summed because the semantics of source rows must be verified before additive aggregation is appropriate.

Mapping example, quality checks, and API parameters are documented in [API docs](api.md).
