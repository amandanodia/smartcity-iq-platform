import logging
import math
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

from app import db
from app.models import (
    AirQuality, City, DataQualityReport, GeographicArea, Infrastructure, MonitoringStation,
    PopulationStatistics, RoadAccident, TrafficStatistics, WaterStatistics,
)

logger = logging.getLogger(__name__)

DOMAIN_MODELS = {
    "air_quality": AirQuality,
    "traffic": TrafficStatistics,
    "traffic_statistics": TrafficStatistics,
    "road_safety": RoadAccident,
    "road_accidents": RoadAccident,
    "water": WaterStatistics,
    "water_statistics": WaterStatistics,
    "population": PopulationStatistics,
    "population_statistics": PopulationStatistics,
    "infrastructure": Infrastructure,
}
DOMAIN_LABELS = {
    "air_quality": "air_quality", "traffic": "traffic", "traffic_statistics": "traffic",
    "road_safety": "road_safety", "road_accidents": "road_safety",
    "water": "water", "water_statistics": "water",
    "population": "population", "population_statistics": "population",
    "infrastructure": "infrastructure",
}


def _key(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _column(frame, name):
    if not name:
        return None
    if name not in frame.columns:
        raise ValueError(f"Configured source column '{name}' is not present in the import.")
    return frame[name]


def _as_text(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def _iso_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    return value


def _build_city_index(mapping):
    cities = City.query.filter_by(is_active=True).all()
    name_candidates = {}
    for city in cities:
        name_candidates.setdefault(_key(city.name), []).append(city)
    by_name = {key: matches[0] for key, matches in name_candidates.items() if len(matches) == 1}
    by_pair = {(_key(city.name), _key(city.state_name)): city for city in cities}
    by_slug = {city.slug: city for city in cities}
    aliases_config = mapping.get("city_aliases") or {}
    if not isinstance(aliases_config, dict):
        raise ValueError("city_aliases must map canonical city names to lists of source aliases.")
    for canonical, aliases in aliases_config.items():
        target = by_slug.get(str(canonical)) or by_name.get(_key(canonical))
        if target is None and isinstance(canonical, str) and "," in canonical:
            city_name, state_name = canonical.split(",", 1)
            target = by_pair.get((_key(city_name), _key(state_name)))
        if target is None:
            raise ValueError(f"City alias target '{canonical}' is not a seeded active city.")
        if not isinstance(aliases, list):
            raise ValueError(f"Aliases for '{canonical}' must be a list.")
        for alias in aliases:
            key = _key(alias)
            existing = by_name.get(key)
            if existing is not None and existing.id != target.id:
                raise ValueError(f"City alias '{alias}' conflicts with an existing city name.")
            by_name[key] = target
            by_pair[(key, _key(target.state_name))] = target
    default_id = mapping.get("default_city_id")
    try:
        numeric_default_id = int(default_id) if default_id is not None else None
    except (TypeError, ValueError):
        raise ValueError("default_city_id must be an integer city ID.")
    if isinstance(default_id, float) and not default_id.is_integer():
        raise ValueError("default_city_id must be an integer city ID.")
    default_city = db.session.get(City, numeric_default_id) if numeric_default_id is not None else None
    if default_id is not None and (default_city is None or not default_city.is_active):
        raise ValueError("default_city_id must refer to an active city.")
    return (by_name, by_pair), default_city


def _build_area_index():
    areas = GeographicArea.query.all()
    result = {}
    for area in areas:
        result.setdefault((area.city_id, _key(area.name)), []).append(area)
    return result


def _domain_field(domain, row, mapping):
    if domain == "air_quality":
        name = "pollutant"
        column_name = mapping.get("pollutant_column")
        constant = mapping.get("pollutant")
    elif domain == "population":
        name = "indicator"
        column_name = mapping.get("indicator_column") or mapping.get("measure_column")
        constant = mapping.get("indicator") or mapping.get("measure")
    elif domain == "infrastructure":
        name = "asset_type"
        column_name = mapping.get("asset_type_column") or mapping.get("measure_column")
        constant = mapping.get("asset_type") or mapping.get("measure")
    else:
        name = "measure"
        column_name = mapping.get("measure_column")
        constant = mapping.get("measure")
    value = _as_text(row.get(column_name)) if column_name else _as_text(constant)
    if not value:
        raise ValueError(f"A non-empty {name} mapping is required for this row.")
    max_lengths = {"pollutant": 40, "measure": 100, "indicator": 120, "asset_type": 100}
    if len(value) > max_lengths[name]:
        raise ValueError(f"The mapped {name} exceeds {max_lengths[name]} characters.")
    return name, value


def process_import_batch(batch, mapping):
    if not isinstance(mapping, dict):
        raise ValueError("mapping must be a JSON object.")
    batch = db.session.query(type(batch)).filter_by(id=batch.id).with_for_update().populate_existing().one()
    domain_key = _key(batch.dataset.domain).replace(" ", "_")
    model = DOMAIN_MODELS.get(domain_key)
    domain = DOMAIN_LABELS.get(domain_key)
    if model is None or domain is None:
        raise ValueError(f"Dataset domain '{batch.dataset.domain}' has no Phase 4 normalization pipeline.")
    if not mapping.get("value_column"):
        raise ValueError("mapping.value_column is required.")
    if batch.status in {"processing", "processed", "processed_with_warnings"}:
        raise ValueError(f"Import batch is already {batch.status}.")

    raw_rows = [record.row_data for record in sorted(batch.raw_records, key=lambda item: item.row_number)]
    if not raw_rows:
        raise ValueError("Import batch contains no raw rows.")
    frame = pd.DataFrame(raw_rows)
    for field in ("pollutant_column", "indicator_column", "measure_column", "asset_type_column",
                  "asset_name_column", "station_id_column"):
        if mapping.get(field):
            _column(frame, mapping[field])
    value_source = _column(frame, mapping.get("value_column"))
    date_source = _column(frame, mapping.get("date_column")) if mapping.get("date_column") else None
    year_source = _column(frame, mapping.get("reference_year_column")) if mapping.get("reference_year_column") else None
    city_source = _column(frame, mapping.get("city_column")) if mapping.get("city_column") else None
    state_source = _column(frame, mapping.get("state_column")) if mapping.get("state_column") else None
    area_source = _column(frame, mapping.get("geographic_area_column")) if mapping.get("geographic_area_column") else None
    unit_source = _column(frame, mapping.get("unit_column")) if mapping.get("unit_column") else None
    id_source = _column(frame, mapping.get("source_record_id_column")) if mapping.get("source_record_id_column") else None
    source_timezone = mapping.get("source_timezone")
    if source_timezone:
        try:
            source_tz = ZoneInfo(source_timezone)
        except (ZoneInfoNotFoundError, TypeError):
            raise ValueError("source_timezone must be a valid IANA timezone name.")
    else:
        source_tz = None
    year_values = pd.to_numeric(year_source.replace("", np.nan), errors="coerce") if year_source is not None else None
    if domain == "air_quality" and date_source is None:
        raise ValueError("air_quality requires a date_column; annual year-only data cannot be treated as dated measurements.")
    if domain in {"traffic", "road_safety", "water"} and date_source is None and year_source is None:
        raise ValueError("This dataset requires a date_column or reference_year_column.")
    numeric_values = pd.to_numeric(value_source.replace("", np.nan), errors="coerce")
    city_index, default_city = _build_city_index(mapping)
    area_index = _build_area_index() if area_source is not None else {}
    conversion = mapping.get("unit_conversion")
    if conversion is not None:
        if not isinstance(conversion, dict) or not conversion.get("from_unit") or not conversion.get("to_unit"):
            raise ValueError("unit_conversion requires from_unit and to_unit.")
        factor = float(conversion.get("factor", 1))
        offset = float(conversion.get("offset", 0))
        if not math.isfinite(factor) or factor <= 0 or not math.isfinite(offset):
            raise ValueError("unit_conversion factor must be positive and factor/offset must be finite.")
    else:
        factor, offset = 1.0, 0.0
        if mapping.get("normalized_unit"):
            raise ValueError("normalized_unit requires an explicit unit_conversion rule.")

    frame_duplicate_mask = frame.duplicated(keep="first")
    duplicate_rows = int(frame_duplicate_mask.sum())
    existing_ids = set()
    id_values = [_as_text(value) for value in id_source.tolist()] if id_source is not None else []
    unique_source_ids = sorted({value for value in id_values if value})
    for offset in range(0, len(unique_source_ids), 5000):
        chunk = unique_source_ids[offset:offset + 5000]
        existing_ids.update(row[0] for row in db.session.query(model.source_record_id).filter(
            model.dataset_id == batch.dataset_id, model.source_record_id.in_(chunk)
        ).all())

    staged = []
    rejection_counts = {}
    missing_value_count = 0
    duplicate_id_count = 0
    seen_ids = set()
    raw_records = sorted(batch.raw_records, key=lambda item: item.row_number)
    for i, raw_record in enumerate(raw_records):
        if bool(frame_duplicate_mask.iloc[i]):
            continue
        row = frame.iloc[i].to_dict()
        try:
            city = default_city
            if city_source is not None:
                city_name = _as_text(city_source.iloc[i])
                if state_source is not None:
                    city_state = _as_text(state_source.iloc[i])
                    city = city_index[1].get((_key(city_name), _key(city_state))) if city_name and city_state else None
                else:
                    city = city_index[0].get(_key(city_name)) if city_name else None
                if city is None:
                    raise ValueError("city_missing_or_unmatched")

            area = None
            if area_source is not None:
                area_name = _as_text(area_source.iloc[i])
                candidates = area_index.get((city.id if city else None, _key(area_name)), []) if area_name else []
                if len(candidates) != 1:
                    raise ValueError("geographic_area_missing_or_ambiguous")
                area = candidates[0]

            raw_number = numeric_values.iloc[i]
            if pd.isna(raw_number):
                missing_value_count += 1
                raise ValueError("value_missing_or_non_numeric")
            original_value = float(raw_number)
            if not math.isfinite(original_value):
                raise ValueError("value_not_finite")

            original_unit = _as_text(unit_source.iloc[i]) if unit_source is not None else _as_text(mapping.get("unit"))
            if original_unit and len(original_unit) > 80:
                raise ValueError("unit_too_long")
            if conversion:
                if original_unit != str(conversion["from_unit"]):
                    raise ValueError("unit_does_not_match_conversion_rule")
                normalized_value = original_value * factor + offset
                normalized_unit = str(conversion["to_unit"])
            else:
                normalized_value = original_value
                normalized_unit = original_unit
            if normalized_unit and len(normalized_unit) > 80:
                raise ValueError("normalized_unit_too_long")

            observed_at = None
            reference_year = None
            raw_year = _as_text(year_source.iloc[i]) if year_source is not None else None
            if year_source is not None and raw_year and pd.isna(year_values.iloc[i]):
                raise ValueError("reference_year_invalid")
            if year_values is not None and not pd.isna(year_values.iloc[i]):
                year_num = float(year_values.iloc[i])
                if not year_num.is_integer() or year_num < 1800 or year_num > 2200:
                    raise ValueError("reference_year_invalid")
                reference_year = int(year_num)
            raw_date = _as_text(date_source.iloc[i]) if date_source is not None else None
            if raw_date:
                parsed_date = pd.to_datetime(raw_date, errors="coerce", format=mapping.get("date_format"),
                                             dayfirst=bool(mapping.get("dayfirst", False)))
                if pd.isna(parsed_date):
                    raise ValueError("observation_date_missing_or_invalid")
                if parsed_date.tzinfo is None:
                    if source_tz is None:
                        raise ValueError("source_timezone_required_for_naive_dates")
                    parsed_date = parsed_date.tz_localize(source_tz, ambiguous="NaT", nonexistent="NaT")
                    if pd.isna(parsed_date):
                        raise ValueError("observation_timezone_ambiguous_or_nonexistent")
                if reference_year is None:
                    reference_year = parsed_date.year
                observed_at = parsed_date.tz_convert("UTC").to_pydatetime()
            if domain == "air_quality" and observed_at is None:
                raise ValueError("observation_date_missing_or_invalid")
            if domain in {"traffic", "road_safety", "water"} and observed_at is None and reference_year is None:
                raise ValueError("observation_date_or_year_missing_or_invalid")
            if domain == "population" and reference_year is None:
                raise ValueError("reference_year_missing_or_invalid")

            source_record_id = _as_text(id_source.iloc[i]) if id_source is not None else None
            if source_record_id and len(source_record_id) > 240:
                raise ValueError("source_record_id_too_long")
            if source_record_id and (source_record_id in existing_ids or source_record_id in seen_ids):
                duplicate_id_count += 1
                raise ValueError("duplicate_source_record_id")

            _, field_value = _domain_field(domain, row, mapping)
            metadata = {"raw_import_batch_id": batch.id, "raw_row_number": raw_record.row_number,
                        "source_fields": {str(k): _iso_value(v) for k, v in row.items()},
                        "unit_conversion": conversion, "source_timezone": source_timezone}
            values = {
                "dataset_id": batch.dataset_id,
                "city_id": city.id if city else None,
                "geographic_area_id": area.id if area else None,
                "observed_at": observed_at,
                "source_record_id": source_record_id,
                "original_value": original_value,
                "original_unit": original_unit,
                "normalized_value": normalized_value,
                "normalized_unit": normalized_unit,
                "source_reference": batch.dataset.source_url,
                "metadata_json": metadata,
            }
            if domain == "air_quality":
                values["pollutant"] = field_value
                station_id_column = mapping.get("station_id_column")
                if station_id_column:
                    station_id = _as_text(row.get(station_id_column))
                    station = MonitoringStation.query.filter_by(dataset_id=batch.dataset_id, source_station_id=station_id).one_or_none() if station_id else None
                    values["station_id"] = station.id if station else None
                    if station_id and station is None:
                        metadata["station_resolution_warning"] = "source station ID did not match a registered station"
            elif domain == "population":
                values["indicator"] = field_value
                values["reference_year"] = reference_year
            elif domain == "infrastructure":
                values["asset_type"] = field_value
                asset_name_column = mapping.get("asset_name_column")
                values["asset_name"] = _as_text(row.get(asset_name_column)) if asset_name_column else None
            else:
                values["measure"] = field_value
                if domain in {"road_safety", "traffic", "water"} and reference_year is not None and observed_at is None:
                    values["period_end"] = date(reference_year, 12, 31)
            if not math.isfinite(normalized_value):
                raise ValueError("normalized_value_not_finite")
            if source_record_id:
                seen_ids.add(source_record_id)
            staged.append(model(**values))
        except (ValueError, TypeError) as exc:
            reason = str(exc)
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    db.session.add_all(staged)
    report = DataQualityReport.query.filter_by(import_batch_id=batch.id).order_by(DataQualityReport.id.desc()).first()
    if report is None:
        report = DataQualityReport(dataset_id=batch.dataset_id, import_batch_id=batch.id)
        db.session.add(report)
    report.rows_checked = len(raw_records)
    report.duplicate_rows = duplicate_rows + duplicate_id_count
    warnings = [f"{count} row(s) rejected: {reason}." for reason, count in sorted(rejection_counts.items())]
    if duplicate_rows:
        warnings.append(f"{duplicate_rows} exact duplicate row(s) were excluded from normalized storage; raw rows remain preserved.")
    if duplicate_id_count:
        warnings.append(f"{duplicate_id_count} row(s) reused a source record ID and were excluded.")
    if any(not row.normalized_unit for row in staged):
        warnings.append("Some accepted measurements have no declared unit and cannot be compared safely across datasets.")
    prior_warnings = [warning for warning in (report.warnings or [])
                      if not warning.startswith("Rows are staged as source-shaped raw data; domain normalization has not run.")]
    report.warnings = prior_warnings + warnings
    report.generated_at = datetime.now(timezone.utc)
    batch.rows_inserted = len(staged)
    batch.rows_rejected = sum(rejection_counts.values()) + duplicate_rows
    batch.status = "processed_with_warnings" if warnings or duplicate_rows else "processed"
    batch.finished_at = datetime.now(timezone.utc)
    batch.summary_json = {
        **(batch.summary_json or {}),
        "normalization": {"domain": domain, "mapping": mapping, "rows_checked": len(raw_records),
                          "rows_inserted": len(staged), "rows_rejected": batch.rows_rejected,
                          "duplicate_exact_rows": duplicate_rows, "duplicate_source_ids": duplicate_id_count,
                          "missing_values_rejected": missing_value_count, "rejection_counts": rejection_counts},
    }
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Normalization write failed for import_batch_id=%s", batch.id)
        raise
    logger.info("Import batch normalized: batch_id=%s domain=%s inserted=%s rejected=%s duplicates=%s",
                batch.id, domain, len(staged), batch.rows_rejected, duplicate_rows + duplicate_id_count)
    return {"domain": domain, "rows_checked": len(raw_records), "rows_inserted": len(staged),
            "rows_rejected": batch.rows_rejected, "duplicate_exact_rows": duplicate_rows,
            "duplicate_source_ids": duplicate_id_count, "missing_values_rejected": missing_value_count,
            "rejection_counts": rejection_counts, "status": batch.status}
