# API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check API process and PostgreSQL connectivity. Returns `200` with `{"status":"ok","database":"connected"}` or `503` with a database unavailable status. |
| `GET` | `/api/cities` | List active city records. |
| `GET` | `/api/cities/{id}` | Read one city or return `404`. |
| `GET` | `/api/datasets` | Paginated dataset list; optional `domain`, `city_id`, `page`, and `per_page` filters. |
| `GET` | `/api/datasets/coverage` | Dataset coverage records; optional `city_id` filter. |
| `GET` | `/api/data-sources` | List registered providers and attribution/license metadata. |
| `GET` | `/api/monitoring-stations` | Return station records with validated coordinates; optional `city_id`, `dataset_id`, and `area_id`; capped at 500. |
| `GET` | `/api/geographic-areas` | List registered station/ward/city/district/state areas; optional `city_id` and `area_type`; capped at 1000. |
| `GET` | `/api/data-quality` | Paginated quality reports. |
| `POST` | `/api/import/csv` | Multipart upload with `file` and `dataset_id`; accepts CSV/XLS/XLSX and stages raw records. |
| `POST` | `/api/import-batches/{id}/process` | JSON body with an explicit source `mapping`; validates and writes normalized observations while retaining raw staging. |
| `GET` | `/api/analytics/air-quality` | Air quality grouped by city/area, dataset, pollutant, and normalized unit. `air_quality` is also accepted. |
| `GET` | `/api/analytics/traffic` | Traffic statistics grouped by city/area, dataset, measure, and unit. |
| `GET` | `/api/analytics/road-safety` | Road safety grouped by city/area, dataset, measure, and unit. |
| `GET` | `/api/analytics/water` | Water statistics grouped by city/area, dataset, measure, and unit. |
| `GET` | `/api/analytics/population` | Population indicators grouped by city/area, dataset, indicator, and unit. |
| `GET` | `/api/analytics/city-comparison?domain=...` | Same transparent grouped calculations for a selected domain. |

Upload defaults are 20 MiB and 100,000 rows; configure the byte limit with `MAX_IMPORT_BYTES`. Uploads preserve source-shaped cells, retain detected exact duplicate rows, and report missing cells. They do not normalize or add observations to analytics until the processing route runs. Analytics include source, record class, reporting period, geographic coverage, unit, and observation count. Do not map unavailable measurements to zero. Charts are rendered only after the user selects a single dataset, category, unit, and geographic level, so unlike series are not silently combined. The station map only displays stored station coordinates and shows an unavailable state when none match.

Normalization requires a JSON mapping. Example shape (replace the column names with the exact source headers):

```json
{
  "mapping": {
    "value_column": "PM2.5 (ug/m3)",
    "date_column": "Date",
    "source_timezone": "<IANA timezone used by the source>",
    "city_column": "City",
    "pollutant": "PM2.5",
    "unit_column": "Unit",
    "source_record_id_column": "Record ID"
  }
}
```

Replace the timezone placeholder only after verifying the source's timestamp convention.

Optional mappings include `reference_year_column`, `geographic_area_column`, `default_city_id`, `city_aliases` (target by canonical name, `name, state`, or city slug), `state_column`, and domain fields such as `measure`, `pollutant`, `indicator`, or `asset_type` (or their `*_column` forms). For cities sharing a name, supply both city and state columns. Naive timestamps require an explicit IANA `source_timezone`; timezone-aware timestamps are converted to UTC. Use `date_format` and `dayfirst` when the source format needs them. Unit conversions must explicitly specify `unit_conversion: {"from_unit": "...", "to_unit": "...", "factor": 1, "offset": 0}`. Without a conversion rule, numeric values retain their original unit. Analytics group by dataset, geography, category, and unit. Date filters use `timezone=UTC` by default and can be given an IANA timezone. A comparable highest-recorded city insight is produced only when the request filters one dataset, category, unit, and geographic level. No route infers causation or combines different units.
